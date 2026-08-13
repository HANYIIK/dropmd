from pathlib import Path


application = defines.get("app", "dist/DropMD.app")
application_name = Path(application).name

files = [application]
symlinks = {"Applications": "/Applications"}
icon_locations = {application_name: (145, 150), "Applications": (495, 150)}
background = "builtin-arrow"
window_rect = ((160, 160), (640, 320))
default_view = "icon-view"
show_icon_preview = False
show_status_bar = False
show_tab_view = False
show_toolbar = False
show_pathbar = False
show_sidebar = False
icon_size = 112
text_size = 13
label_pos = "bottom"
format = "UDZO"
filesystem = "HFS+"
