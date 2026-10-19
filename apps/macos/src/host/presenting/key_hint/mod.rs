//! 双拼键位提示：按 `[general] key_hint` 决定这一帧画不画键盘，把 Core 给的键位换成渲染器的键盘。

mod state;
mod timer;

pub use state::KeyHintState;

use objc2::MainThreadMarker;
use qingjian_core::shuangpin::{KeyHint, KeyState};
use qingjian_platform::KeyHintMode;
use qingjian_render::{Keyboard, Keycap, KeycapState};

use super::super::Host;

impl Host {
    /// 这一帧的键盘；不该画时为 `None`。组句结束（缓冲区空了）时清掉「卡住时显示」的状态。
    pub(in crate::host) fn key_hint_keyboard(&mut self) -> Option<Keyboard> {
        let hint = (self.key_hint_mode != KeyHintMode::Off
            && self.translation.is_none()
            && !self.engine.composition().is_empty())
        .then(|| self.engine.key_hint())
        .flatten();
        let Some(hint) = hint else {
            self.key_hint = KeyHintState::default();
            return None;
        };
        let show = match self.key_hint_mode {
            KeyHintMode::Always => true,
            KeyHintMode::Auto => {
                let mtm = MainThreadMarker::new().expect("Host 只在主线程用");
                let typed = self.engine.composition().text().to_owned();
                self.key_hint.update(mtm, &typed, hint.stuck)
            }
            KeyHintMode::Off => false,
        };
        show.then(|| keyboard(&hint))
    }

    /// 停顿计时到点：还在组句就弹出键盘。
    pub fn key_hint_hesitated(&mut self) {
        if self.engine.composition().is_empty() {
            return;
        }
        self.key_hint.hesitated();
        self.render();
    }
}

fn keyboard(hint: &KeyHint) -> Keyboard {
    let rows = hint
        .rows
        .iter()
        .map(|row| {
            row.iter()
                .map(|cap| Keycap {
                    label: cap.key.to_ascii_uppercase().to_string(),
                    corner: cap.initial.map(str::to_owned),
                    lines: cap.finals.clone(),
                    state: match &cap.state {
                        KeyState::Idle => KeycapState::Normal,
                        KeyState::Pressed => KeycapState::Pressed,
                        KeyState::Next(syllable) => KeycapState::Next(syllable.clone()),
                        KeyState::Unavailable => KeycapState::Dimmed,
                    },
                })
                .collect()
        })
        .collect();
    Keyboard { rows }
}
