//! 双拼键位提示的数据：壳按它画键盘，什么时候弹出由壳按配置决定。

use super::Engine;
use crate::shuangpin::KeyHint;

impl Engine {
    /// 开着双拼、缓冲区在解拼音时才有；英文、直输、表达式、问字、辅码与符号面板都不画。
    /// 光标停在中间时按光标前的那段算，与候选一致。
    pub fn key_hint(&self) -> Option<KeyHint> {
        let scheme = self.shuangpin?;
        if self.zhuyin
            || self.english_mode()
            || self.raw_mode()
            || self.expression_mode()
            || self.question_mode()
            || self.in_aux()
            || self.panel.is_some()
        {
            return None;
        }
        Some(KeyHint::for_keys(scheme, self.composition.scope()))
    }
}
