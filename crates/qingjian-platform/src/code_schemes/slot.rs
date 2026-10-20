//! 壳手里「现在装着哪套形码方案」：按配置的两条轴装配引擎，方案与码表文件都没变时不重读码表。
//!
//! 每次配置热加载都会走到这里，而大多数时候改的是别的设置；8.9 万条的码表每次重读一遍是白花的。

use std::path::Path;
use std::time::SystemTime;

use qingjian_core::Engine;

use super::{CodeSchemeEntry, find};
use crate::Scheme;

/// 码表文件的修改时间与长度：两者都没变就当没改。
type Stamp = (Option<SystemTime>, u64);

/// 当前装上的方案与它码表文件的指纹；没开形码或没装上为 `None`。
#[derive(Debug, Default)]
pub struct CodeSchemeSlot {
    loaded: Option<(CodeSchemeEntry, Stamp)>,
}

impl CodeSchemeSlot {
    /// 按配置装配引擎：拼音侧（全拼 / 双拼 / 注音 / 关）与形码侧（`code` 是方案 id，`None` 为关）。
    /// 两边都开就是混输，见 `Engine::query_mixed`。
    ///
    /// 开了形码但方案找不到或码表读不了时警告并退回只用拼音（配置说五笔、引擎一个字都打不出更糟）。
    /// 每次都重新找方案（用户可能刚换了方案、刚放进新方案），但找到的与装着的是同一套、码表文件也没动时不重读。
    /// `bundled` 是随包的 `schemes` 目录。
    pub fn apply(
        &mut self,
        engine: &mut Engine,
        pinyin: Scheme,
        code: Option<&str>,
        user_dir: Option<&Path>,
        bundled: Option<&Path>,
    ) {
        engine.set_shuangpin(pinyin.shuangpin());
        engine.set_zhuyin_mode(pinyin == Scheme::Zhuyin);
        let entry = code.and_then(|id| {
            let found = find(id, user_dir, bundled);
            if found.is_none() {
                tracing::warn!(id, "选了形码方案但找不到，仍按拼音输入");
            }
            found
        });
        let wanted = entry.map(|entry| {
            let stamp = stamp(&entry.table);
            (entry, stamp)
        });
        let unchanged = wanted.is_some() && wanted == self.loaded && engine.code_scheme().is_some();
        if !unchanged {
            self.loaded = wanted.and_then(|(entry, stamp)| match entry.load() {
                Ok(scheme) => {
                    tracing::info!(
                        id = %entry.id,
                        table = %entry.table.display(),
                        entries = scheme.table.len(),
                        "形码方案已载入"
                    );
                    engine.set_code_scheme(Some(scheme));
                    Some((entry, stamp))
                }
                Err(error) => {
                    tracing::error!(%error, table = %entry.table.display(), "形码码表读不了，仍按拼音输入");
                    None
                }
            });
            if self.loaded.is_none() {
                engine.set_code_scheme(None);
            }
        }
        // 拼音侧关掉且形码装上了才是「只用形码」；两边都没有时留拼音兜底（否则一个候选都没有）
        engine.set_phonetic(pinyin.is_on() || self.loaded.is_none());
    }

    /// 装上的方案的名字，状态条与主题显示用。
    pub fn label(&self) -> Option<&str> {
        self.loaded.as_ref().map(|(entry, _)| entry.label.as_str())
    }
}

fn stamp(path: &Path) -> Stamp {
    std::fs::metadata(path).map_or((None, 0), |metadata| {
        (metadata.modified().ok(), metadata.len())
    })
}
