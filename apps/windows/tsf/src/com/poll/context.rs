//! 轮询定时器每一拍回调要用的东西：按消息窗口句柄从线程表里查出来。

use std::cell::Cell;
use std::rc::Rc;

use crate::com::composition::Shared;
use crate::com::service::SharedClient;

pub(super) struct PollContext {
    /// 引擎层：拉云结果 / 问切模式请求。
    pub(super) engine: SharedClient,

    /// 组句状态：在不在组句 / 翻译评审 / 前台。
    pub(super) shared: Rc<Shared>,

    /// 拍数计数，给 [`MODE_SYNC_EVERY`](super::MODE_SYNC_EVERY) 取模。
    pub(super) ticks: Cell<u32>,

    /// 当前线程是否处于独立英语键盘布局。
    pub(super) english_layout: Cell<bool>,

    /// 本服务的 TSF client id：点击上屏要申请编辑会话。
    pub(super) client_id: u32,
}
