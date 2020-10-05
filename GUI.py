import PySimpleGUI as sg

sg.theme("Dark")

class main_window:
    def __init__(self, restart, threads, name):
        self.restart = restart
        self.threads = threads
        self.name = name
        status_layout = [
            [sg.Col([[sg.Text(name)], [sg.Text('Running' if thread.is_alive() else 'Stopped', text_color='Green' if thread.is_alive() else 'Red', key=f'{name}_STATUS')]]), sg.Button("Restart", key=f"{name}_RESTART", disabled=thread.is_alive())] for name, thread in threads.items()
        ]
        layout = [
            [sg.Listbox([], key="CONSOLE", size=(75, 30), background_color="Black", text_color="White"), sg.Frame("Internal Status", status_layout)]
        ]
        self.window = sg.Window(name, layout)
        self.is_running = True
        self.read = self.window.read
        self.request_console_update = False
        self.request_ui_update = False
        self.console = []

    def write(self, text):
        self.console.append(text)
        self.request_console_update = True

    def update_UI(self, data):
        self.threads = data
        self.request_ui_update = True

    def close(self):
        self.is_running = False
        self.window.Close()

    def work(self, event):
        if event == sg.WINDOW_CLOSED:
            self.close()
        elif "RESTART" in event:
            self.restart(event.replace('_RESTART', ''))
        
        if self.request_console_update:
            self.window["CONSOLE"].Update(self.console)
            self.request_console_update = False
        if self.request_ui_update:
            for name, thread in self.threads.items():
                self.window[f"{name}_STATUS"].Update('Running' if thread.is_alive() else 'Stopped')
                self.window[f"{name}_STATUS"].Update(text_color='Green' if thread.is_alive() else 'Red')
                self.window[f"{name}_RESTART"].Update(disabled=thread.is_alive())
            self.request_ui_update = False

    def show(self):
        while self.is_running:
            event, _ = self.read(timeout=1)
            print(event)
            self.work(event)

if __name__=="__main__":
    def restart(name):
        print(f"{name}_restart")
        th[name].alive = not th[name].alive
        GUI.update_UI(th)
    class asd:
        def __init__(self, is_alive):
            self.alive = is_alive
        def is_alive(self):
            return self.alive
    th = {"name":asd(True), "mame2":asd(False)}
    GUI = main_window(restart, th, "Test")
    print = GUI.write
    GUI.show()