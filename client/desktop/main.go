package main

import (
	"embed"

	"github.com/wailsapp/wails/v2"
	"github.com/wailsapp/wails/v2/pkg/options"
	"github.com/wailsapp/wails/v2/pkg/options/assetserver"
)

//go:embed all:frontend/dist
var assets embed.FS

func main() {
	app := NewApp()
	if err := app.Initialize(); err != nil {
		println("desktop init error:", err.Error())
		return
	}
	defer app.Shutdown()

	err := wails.Run(&options.App{
		Title:    "Perseus Desktop",
		Width:    1280,
		Height:   800,
		MinWidth: 940,
		MinHeight: 620,
		// 自定义标题栏：移除原生边框。拖动由前端把 --wails-draggable 标为 drag 触发
		// (wails 注入代码 → WM_NCLBUTTONDOWN/HTCAPTION)，缩放由分割默认的 6px 边缘感知。
		Frameless: true,
		AssetServer: &assetserver.Options{
			Assets: assets,
		},
		BackgroundColour: &options.RGBA{R: 27, G: 38, B: 54, A: 1},
		OnStartup:        app.startup,
		Bind: []interface{}{
			app,
		},
	})
	if err != nil {
		println("Error:", err.Error())
	}
}
