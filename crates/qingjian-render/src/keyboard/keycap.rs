//! 一个键：左上键名，右上角标，下方几行小字。

use super::KeycapState;

#[derive(Debug, Clone, PartialEq)]
pub struct Keycap {
    /// 键名（`Q`、`;`）。
    pub label: String,

    /// 右上角标（翘舌声母）。
    pub corner: Option<String>,

    /// 下方的小字，一项一行（韵母）；[`KeycapState::Next`] 时改画那个音节。
    pub lines: Vec<String>,

    pub state: KeycapState,
}
