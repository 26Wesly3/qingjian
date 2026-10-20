//! 辅码码表：随包的（随包根 `codes/`）与用户目录 `codes/` 下的 `.qj`，连同 `schemes/` 里的辅码方案，
//! 按 `[aux_code] scheme` 挑一套接到 Engine 上。

mod source;
mod sources;

pub use source::AuxSource;
pub use sources::AuxCodeSources;

use std::path::{Path, PathBuf};

/// 码表的扩展名：只认打包过的 `.qj`（TSV 在导入时就转掉了）。
const EXTENSION: &str = "qj";

/// 列出目录里的码表文件（按文件名排序），返回 (文件名不含扩展名, 路径)。目录不存在就是空。
pub fn list(dir: &Path) -> Vec<(String, PathBuf)> {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return Vec::new();
    };
    let mut files: Vec<(String, PathBuf)> = entries
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter_map(|path| {
            (path.extension()?.to_str()? == EXTENSION).then(|| {
                let stem = path.file_stem()?.to_str()?.to_owned();
                Some((stem, path))
            })?
        })
        .collect();
    files.sort();
    files
}
