//! 在 Windows 上编时给 DLL 嵌版本信息：代码签名要求每个被签的文件带产品名与版本号，资源管理器的「详细信息」里也看得到。

fn main() {
    embed_version();
}

/// 资源要 `rc.exe`（MSVC）编，只在 Windows 宿主上做；失败只警告，别让编译挂掉。
#[cfg(windows)]
fn embed_version() {
    if let Err(error) = winresource::WindowsResource::new()
        .set("ProductName", "青简")
        .set("FileDescription", "青简输入法文本服务")
        .compile()
    {
        println!("cargo:warning=嵌入 TSF DLL 版本信息失败: {error}");
    }
}

#[cfg(not(windows))]
fn embed_version() {}
