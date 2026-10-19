//! 双拼键位提示：几排圆角键错位排开，每个键左上键名、右上角标、下方几行小字，按状态换填充与文字颜色。
//! 排法固定，尺寸与颜色取主题的 `keyboard` 分节；整块的透明度由壳设在窗口上，这里不管。

use bamboo_slip::taffy::NodeId;
use bamboo_slip::taffy::{Dimension, LengthPercentageAuto, Position, Rect, Size, Style};
use bamboo_slip::{Color, Effect, FontSpec, RenderError, Scene, TextStyle, Visual};

use super::{Rendered, Renderer};
use crate::keyboard::{Keyboard, Keycap, KeycapState};
use crate::theme::file::ColorSpec;
use crate::theme::file::node::EffectSpec;
use crate::theme::{TextSizes, Theme};

/// 第二、三排相对第一排右移几个键宽，与常见键盘的错位一致。
const ROW_OFFSETS: [f32; 3] = [0.0, 0.3, 0.8];

/// 键内文字离键边的距离（点）。
const INSET: f32 = 4.0;

/// 一次渲染里按倍数换算好的参数。
struct Metrics<'a> {
    theme: &'a Theme,

    scale: f32,

    key_font: FontSpec,

    label_font: FontSpec,
}

impl Metrics<'_> {
    fn px(&self, points: f32) -> f32 {
        points * self.scale
    }

    fn style(&self, font: FontSpec, color: Color) -> TextStyle {
        TextStyle::new(
            font.scaled(self.scale),
            font.size,
            color,
            self.theme.text_gamma(),
        )
    }
}

/// 一个键各部分的颜色。
struct Paint {
    fill: Color,

    key: Color,

    corner: Color,

    lines: Color,
}

impl Renderer {
    /// 画键位提示键盘。整块跟着候选字的比例缩放，再乘 `zoom`（用户设的大小，1 为原大）。
    /// 位图仍按 `scale` 标记，壳换回点时放大的部分留在点数里。
    pub fn render_keyboard(
        &mut self,
        keyboard: &Keyboard,
        theme: &Theme,
        scale: f32,
        zoom: f32,
    ) -> Result<Rendered, RenderError> {
        let screen_scale = scale;
        let scale = scale * theme.candidate_scale() * zoom;
        let theme = &theme.with_text_sizes(TextSizes::default());
        self.stage.text().use_families(theme.families());
        let spec = &theme.file().keyboard;
        let m = Metrics {
            theme,
            scale,
            key_font: theme.font_ref(&spec.key_font),
            label_font: theme.font_ref(&spec.label_font),
        };
        let (key_w, key_h, gap, padding) = (
            m.px(spec.key_width),
            m.px(spec.key_height),
            m.px(spec.gap),
            m.px(spec.padding),
        );

        let mut scene = Scene::new();
        let mut keys = Vec::new();
        let mut width: f32 = 0.0;
        for (row_index, row) in keyboard.rows.iter().enumerate() {
            let offset = ROW_OFFSETS.get(row_index).copied().unwrap_or(0.0) * key_w;
            let top = padding + row_index as f32 * (key_h + gap);
            for (i, cap) in row.iter().enumerate() {
                let left = padding + offset + i as f32 * (key_w + gap);
                keys.push(key(&mut scene, cap, &m, (left, top), (key_w, key_h))?);
                width = width.max(left + key_w);
            }
        }
        let content_width = (width + padding).ceil();
        let rows = keyboard.rows.len() as f32;
        let content_height = (padding * 2.0 + rows * key_h + (rows - 1.0).max(0.0) * gap).ceil();
        let root = scene.node(
            Style {
                size: Size {
                    width: Dimension::length(content_width),
                    height: Dimension::length(content_height),
                },
                ..Style::default()
            },
            Visual::solid(theme.color(&spec.background), m.px(spec.radius)),
            &keys,
        )?;
        let effects = spec
            .effects
            .iter()
            .map(|effect| effect_of(effect, &m))
            .collect();
        scene.set_effects(root, effects);
        scene.layout(root, self.stage.text())?;
        Ok(Rendered::new(
            self.stage
                .rasterize(&scene, root, (content_width, content_height), screen_scale)?,
            Vec::new(),
        ))
    }
}

/// 键盘没有数据条件，条件颜色取 `else` 分支。
fn effect_of(spec: &EffectSpec, m: &Metrics) -> Effect {
    let color = match &spec.shadow().color {
        ColorSpec::Fixed(color)
        | ColorSpec::Switch {
            otherwise: color, ..
        } => color,
    };
    spec.to_effect(m.scale, m.theme.color(color))
}

fn paint(state: &KeycapState, m: &Metrics) -> Paint {
    let spec = &m.theme.file().keyboard;
    let color = |c| m.theme.color(c);
    match state {
        KeycapState::Normal => Paint {
            fill: color(&spec.key_fill),
            key: color(&spec.key_text),
            corner: color(&spec.initial),
            lines: color(&spec.label),
        },
        KeycapState::Pressed => {
            let text = color(&spec.pressed_text);
            Paint {
                fill: color(&spec.pressed_fill),
                key: text,
                corner: text,
                lines: text,
            }
        }
        KeycapState::Next(_) => Paint {
            fill: color(&spec.next_fill),
            key: color(&spec.key_text),
            corner: color(&spec.initial),
            lines: color(&spec.next_text),
        },
        KeycapState::Dimmed => {
            let text = color(&spec.dimmed_text);
            Paint {
                fill: color(&spec.key_fill),
                key: text,
                corner: text,
                lines: text,
            }
        }
    }
}

/// 一个键：盒子绝对定位在键盘里，键名、角标、小字再绝对定位在盒子里。
fn key(
    scene: &mut Scene,
    cap: &Keycap,
    m: &Metrics,
    (left, top): (f32, f32),
    (width, height): (f32, f32),
) -> Result<NodeId, RenderError> {
    let spec = &m.theme.file().keyboard;
    let paint = paint(&cap.state, m);
    let inset = m.px(INSET);
    let mut children = Vec::with_capacity(2 + cap.lines.len());
    children.push(text(
        scene,
        &cap.label,
        m.style(m.key_font, paint.key),
        absolute((Some(inset), None), Some(inset), None),
    )?);
    if let Some(corner) = &cap.corner {
        children.push(text(
            scene,
            corner,
            m.style(m.label_font, paint.corner),
            absolute((None, Some(inset)), Some(inset), None),
        )?);
    }
    let next;
    let lines: &[String] = match &cap.state {
        KeycapState::Next(syllable) => {
            next = [syllable.clone()];
            &next
        }
        _ => &cap.lines,
    };
    let line_height = m.px(m.label_font.line_height);
    for (i, line) in lines.iter().enumerate() {
        let top = height - inset - (lines.len() - i) as f32 * line_height;
        children.push(text(
            scene,
            line,
            m.style(m.label_font, paint.lines),
            absolute((Some(inset), None), Some(top), None),
        )?);
    }
    let style = absolute((Some(left), None), Some(top), Some((width, height)));
    scene.node(
        style,
        Visual::solid(paint.fill, m.px(spec.key_radius)),
        &children,
    )
}

fn text(
    scene: &mut Scene,
    text: &str,
    style: TextStyle,
    layout: Style,
) -> Result<NodeId, RenderError> {
    scene.node(
        layout,
        Visual::Text {
            text: text.to_owned(),
            style,
        },
        &[],
    )
}

/// 绝对定位：左右只给一边，另一边自动；`size` 不给就按内容量。
fn absolute(
    (left, right): (Option<f32>, Option<f32>),
    top: Option<f32>,
    size: Option<(f32, f32)>,
) -> Style {
    let edge = |value: Option<f32>| {
        value.map_or(LengthPercentageAuto::auto(), LengthPercentageAuto::length)
    };
    Style {
        position: Position::Absolute,
        inset: Rect {
            left: edge(left),
            right: edge(right),
            top: edge(top),
            bottom: LengthPercentageAuto::auto(),
        },
        size: size.map_or(Size::auto(), |(width, height)| Size {
            width: Dimension::length(width),
            height: Dimension::length(height),
        }),
        ..Style::default()
    }
}
