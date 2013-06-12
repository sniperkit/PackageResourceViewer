import sublime
import sublime_plugin
import os
import errno

VERSION = int(sublime.version())

if VERSION >=3006:
    from PackageResourceViewer.package_resources import *
else:
    from package_resources import *

class PackageResourceViewerCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.settings = sublime.load_settings("PackageResourceViewer.sublime-settings")
        self.packages = get_packages_list(True, self.settings.get("ignore_patterns", []))
        self.path = []
        self.path_objs = []
        self.show_quick_panel(self.packages, self.package_list_callback)

    def package_list_callback(self, index):
        if index == -1:
            return

        self.package = self.packages[index]
        ignore_patterns = self.settings.get("ignore_patterns", [])
        self.package_files = {}
        self.quick_panel_files = self.create_quick_panel_file_list(self.package_files)
        self.add_entry_to_path_obj()
        self.show_quick_panel(self.quick_panel_files, self.package_file_callback)

    def add_entry_to_path_obj(self, entry=""):
        if len(self.path_objs) == 0 and entry == "":
            self.path_objs.append(self.package_files)
        else:
            self.path.append(entry)
            self.path_objs.append(self.path_objs[-1][entry])

    def pop_entry_from_path_obj(self):
        if len(self.path_objs) > 0:
            if len(self.path) > 0:
                self.path.pop()
            self.path_objs.pop()

    def is_file(self, entry):
        return len(self.path_objs[-1][entry]) == 0


    def create_quick_panel_file_list(self, files_obj):
        quick_panel_files = [".."]
        if len(files_obj) == 0:
            ignore_patterns = self.settings.get("ignore_patterns", [])
            files_list = list_package_files(self.package, ignore_patterns)
            for entry in files_list:
                self.create_file_entry(entry, self.package_files)
            dirs, files = self.split_dirs_and_files(self.package_files)
        else:
            dirs, files = self.split_dirs_and_files(files_obj)

        quick_panel_files += dirs
        quick_panel_files += files
        return quick_panel_files

    def create_file_entry(self, file_path, obj):
        split_file = file_path.split("/", 1)
        if len(split_file) > 1:
            if split_file[0] not in obj:
                obj[split_file[0]] = {}
            self.create_file_entry(split_file[1], obj[split_file[0]])
        else:
            obj[file_path] = {}

    def split_dirs_and_files(self, obj):
        files = []
        dirs = []

        for key in obj.keys():
            entry = obj[key]
            if len(entry) == 0:
                files.append(key)
            else:
                dirs.append(key + "/")

        return sorted(dirs), sorted(files)

    def package_file_callback(self, index):
        if index == -1:
            return
        entry = self.quick_panel_files[index]
        if entry == "..":
            self.pop_entry_from_path_obj()
            if len(self.path_objs) == 0:
                self.show_quick_panel(self.packages, self.package_list_callback)
            else:
                self.quick_panel_files = self.create_quick_panel_file_list(self.path_objs[-1])
                self.show_quick_panel(self.quick_panel_files, self.package_file_callback)
        else:
            entry = entry.replace("/", "")
            if self.is_file(entry):
                self.pre_open_file_setup(entry)
                view = self.open_file(self.package, "/".join(self.path + [entry]))
                sublime.set_timeout(lambda: self.setup_view(view), 10)
                if self.settings.get("open_multiple", False):
                    self.show_quick_panel(self.quick_panel_files, self.package_file_callback)
            else:
                self.add_entry_to_path_obj(entry)
                self.quick_panel_files = self.create_quick_panel_file_list(self.path_objs[-1])
                self.show_quick_panel(self.quick_panel_files, self.package_file_callback)

    def pre_open_file_setup(self, entry):
        pass

    def setup_view(self, view):
        pass

    def show_quick_panel(self, options, done_callback):
        sublime.set_timeout(lambda: self.window.show_quick_panel(options, done_callback), 10)

    def open_file(self, package, resource):
        resource_path = os.path.join(sublime.packages_path(), package, resource)
        view = self.window.open_file(resource_path)
        if not os.path.exists(resource_path):
            content = get_resource(package, resource)
            sublime.set_timeout(lambda: self.insert_text(content, view), 10)
            view.settings().set("create_dir", True)
        return view

    def insert_text(self, content, view):
        if not view.is_loading():
            view.run_command("insert_content", {"content": content})
        else:
            sublime.set_timeout(lambda: self.insert_text(content, view), 10)

class PackageResourceViewerEvents(sublime_plugin.EventListener):
    def on_pre_save(self, view):
        if view.settings().get("create_dir", False):
            if not os.path.exists(view.file_name()):
                directory = os.path.dirname(view.file_name())
                self.create_folder(directory)

    def create_folder(self, path):
        try:
            os.makedirs(path)
        except OSError as ex:
            if ex.errno != errno.EEXIST:
                raise

class InsertContentCommand(sublime_plugin.TextCommand):
    def run(self, edit, content):
        self.view.insert(edit, 0, content)
