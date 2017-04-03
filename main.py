import libaudioverse
import ui

with libaudioverse.InitializationManager():
    u = ui.Ui()
    print("""Welcome to audiograph.

Enter equations on a line by themselves to heare them graphed.  Commands start with ".".  For a list of commands, type .help.

Type .quit to quit.""")
    u.run()
