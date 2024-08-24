import tkinter.filedialog as fd
import os, subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from tkinterdnd2 import *

import glob
from pprint import pprint
import ffmpeg
import fnmatch

class ToolTip():
    def __init__(self, widget, text="default tooltip"):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Motion>", self.motion)
        self.widget.bind("<Leave>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event):
        self.schedule()

    def motion(self, event):
        self.unschedule()
        self.schedule()

    def leave(self, event):
        self.unschedule()
        self.id = self.widget.after(500, self.hideTooltip)

    def schedule(self):
        if self.tw:
            return
        self.unschedule()
        self.id = self.widget.after(500, self.showTooltip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showTooltip(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)
        x, y = self.widget.winfo_pointerxy()
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.geometry(f"+{x + 10}+{y + 10}")
        label = tk.Label(self.tw, text=self.text,
                         relief="solid", borderwidth=1, justify="left")
        label.pack(ipadx=10)

    def hideTooltip(self):
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()

class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        global iDirPath
        iDirPath = None
        self.master.title("動画圧縮")
        self.master.geometry("320x195")
        self.reset(0)




    def reset(self, event):

        self.labelframe1 = tk.LabelFrame(root, text="", labelanchor="nw", width=300, height=175)
        self.labelframe1.propagate(False)  # 幅と高さを指定する場合はこの設定が必要

        global entry_01
        label1 = ttk.Label(self.labelframe1, text="ファイル:")
        label1.place(x=10, y=10)
        self.entry_01 = ttk.Entry(self.labelframe1, width=38)
        ToolTip(self.entry_01, "動画のパスを入れてください\nドラッグ&ドロップで入れられます")
        self.entry_01.place(x=55, y=10)
        self.entry_01.drop_target_register(DND_FILES)
        self.entry_01.dnd_bind('<<Drop>>', self.drop_01)

        self.label2 = ttk.Label(self.labelframe1, text="入力フォーマット:")
        self.label2.place(x=10, y=40)
        format_in = ("mp4", "mov", "avi", "webm","flv")
        self.comb_format_in = ttk.Combobox(self.labelframe1, values=format_in, height=5, width=7, state="readonly")
        self.comb_format_in.current(0)
        self.comb_format_in.place(x=90, y=40)
        ToolTip(self.comb_format_in,"圧縮する拡張子を選んでください")

        self.Spinbox01 = tk.IntVar(root)
        self.Spinbox01.set(21)
        self.s01 = tk.Spinbox(self.labelframe1, textvariable=self.Spinbox01, from_=0, to=51, increment=1, width=10)
        ToolTip(self.s01,"0~51で選べます。0に近いほど圧縮率が小さくなります。51に近いほど映像が粗くなります\n18~23ぐらいがオススメかも")
        self.label3 = ttk.Label(self.labelframe1, text="圧縮率:")
        self.label3.place(x=160, y=40)
        self.s01.place(x=210, y=40)
        #
        # self.sep = ttk.Separator(self.labelframe1, orient="horizontal", style="blue.TSeparator")
        # self.sep.place(x=0, y=60)
        #
        self.button_mov = tk.Button(self.labelframe1, text="圧縮処理", width=17, command=self.callSubExe)
        self.button_mov.place(x=10, y=75)

        self.button_exit = tk.Button(self.labelframe1, text="終了", width=17, command=self.exit_program)
        self.button_exit.place(x=160, y=75)

        self.label3 = ttk.Label(self.labelframe1, text=" ")
        self.label3.place(x=10, y=105)
        #
        self.progress_var = tk.IntVar()
        self.progress_var.set(0)
        self.progress_bar = ttk.Progressbar(self.labelframe1, orient="horizontal", length=280, mode="determinate",
                                            maximum=100,
                                            variable=self.progress_var)
        self.progress_bar.place(x=10, y=140)
        self.labelframe1.place(x=10, y=10)

    def drop_01(self, drop):
        self.entry_01.delete(0, tk.END)
        if drop.data.startswith('{'):
            self.entry_01.insert(0, drop.data[1:-1])
        else:
            self.entry_01.insert(0, drop.data)

    # -------------------------------------------------------------------------#


    def exit_program(self):

        self.quit()
        exit()

    # -------------------------------------------------------------------------#

    def ask_input_filenames(self, msg=None, types=[('', '*.*')]):
        """
        入力用ファイル名の設定
        """
        rt = tk.Tk()
        rt.withdraw()
        filenames = fd.askopenfilenames(title=msg, filetypes=types)
        rt.destroy()
        return filenames

    def callSubExe(pEntryVal):
        subThread = threading.Thread(target=shrink_mov_files, name='subThread', args=(pEntryVal,))
        subThread.start()

    def subprocess_args(include_stdout=True):
        # The following is true only on Windows.
        if hasattr(subprocess, 'STARTUPINFO'):
            # Windowsでは、PyInstallerから「--noconsole」オプションを指定して実行すると、
            # サブプロセス呼び出しはデフォルトでコマンドウィンドウをポップアップします。
            # この動作を回避しましょう。
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            # Windowsはデフォルトではパスを検索しません。環境変数を渡してください。
            env = os.environ
        else:
            si = None
            env = None

        # subprocess.check_output()では、「stdout」を指定できません。
        # したがって、必要な場合にのみ追加してください。
        if include_stdout:
            ret = {'stdout': subprocess.PIPE}
        else:
            ret = {}

        # Windowsでは、「--noconsole」オプションを使用してPyInstallerによって
        # 生成されたバイナリからこれを実行するには、
        # OSError例外「[エラー6]ハンドルが無効です」を回避するために
        # すべて（stdin、stdout、stderr）をリダイレクトする必要があります。
        ret.update({'stdin': subprocess.PIPE,
                    'stderr': subprocess.PIPE,
                    'startupinfo': si,
                    'env': env})
        return ret

    # -------------------------------------------------------------------------#
def ctrlEvent(event):
    if(event.state & 2**2 == 4 and event.keysym=='c' ):
        return
    else:
        return "break"
def shrink_mov_files(self):
    def find_files(root_dir, extension):
        matches = []
        num = 0
        for root, dirnames, filenames in os.walk(root_dir):
            for filename in fnmatch.filter(filenames, f"*.{extension}"):
                matches.append(os.path.join(root, filename))
                num+=1
        return num
    # 入力ファイルの選択
    filepaths = self.entry_01.get().replace('\\', '/')#self.ask_input_filenames("動画ファイルを選んでください", types=[('', frm_str)])

    # キャンセルされた場合
    if filepaths == '':
        return
    crf = self.Spinbox01.get()
    isfile = os.path.isfile(filepaths)
    if isfile!=True:
        files = glob.glob(f"{filepaths}/*.{self.comb_format_in.get()}")
        i = 0
        num = find_files(filepaths, self.comb_format_in.get())
        for file in files:
            i+=1
            file = file.replace('\\', '/')
            #print(file)
            kakutyoushi = file.split(".")
            kakutyoushi = kakutyoushi[-1]
            #print(kakutyoushi)
            if kakutyoushi == self.comb_format_in.get():
                try:
                    dirname = os.path.dirname(file)
                    base_filename = os.path.splitext(os.path.basename(file))[0]  # 拡張子なしの入力ファイル名
                    os.path.join(dirname)
                    filename=os.path.abspath(os.path.join(dirname, os.pardir))
                    output_file = str(f"{filename}/result/{base_filename}.mp4")
                    if not os.path.exists(f"{filename}/result"):
                        os.makedirs(f"{filename}/result")
                    if not os.path.exists(output_file):
                        command = (f'ffmpeg -i "{file}" -c:a copy -c:v libx265 -crf {crf} "{output_file}"')
                        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,universal_newlines=True,encoding='utf-8')
                        probe = ffmpeg.probe(file)
                        for stream in probe['streams']:
                            #print('stream {0}: {1}'.format(stream['index'], stream['codec_type']))
                            if stream["codec_type"] == 'video':
                                #pprint(stream)  # Python3.8からsort_dicts=Falseが使える
                                for line in p.stdout:
                                    #self.info.insert(tk.END, f"{line}\n")
                                    if line[:7] == "frame= ":
                                        idx = line.find("fps=")
                                        frame = line[:idx].replace(' ', '')
                                        frame = int(frame.replace('frame=', ''))
                                        # print(frame)
                                        # print(stream['nb_frames'])
                                        # print(stream['duration_ts'])
                                        total = int(stream['nb_frames'])
                                        pow = (frame/total)*100.0
                                        #print(f"進捗:{pow}%")
                                        self.progress_var.set(pow)
                                        if pow != 100:
                                            self.label3["text"] = f"{base_filename}\n 圧縮中:{pow}% {i}/{num} "
                                            print(f"{base_filename}\n 圧縮中:{pow}% {i}/{num} ")
                                        if pow == 100:
                                            self.label3["text"] = f"{base_filename}\n圧縮完了"
                                            print(f"{base_filename}\n圧縮完了")

                        try:
                            outs, errs = p.communicate()
                        except subprocess.TimeoutExpired:
                            pass
                        else:
                            p.terminate()

                except Exception as error:
                    print(error.args)
                    messagebox.showinfo("動画ファイル圧縮エラー", "動画ファイル圧縮中にエラーが発生しました。")
                    return
    if isfile==True:
        kakutyoushi = filepaths.replace('\\', '/').split(".")
        kakutyoushi = kakutyoushi[-1]
        input_file = filepaths.replace('\\', '/')
        if kakutyoushi == self.comb_format_in.get():
            try:
                dirname = os.path.dirname(input_file)
                base_filename = os.path.splitext(os.path.basename(input_file))[0]  # 拡張子なしの入力ファイル名
                os.path.join(dirname)
                output_file = str(f"{dirname}/{base_filename}_圧縮.mp4")
                #print(input_file)
                if not os.path.exists(output_file):
                    command = (f'ffmpeg -i "{input_file}" -c:a copy -c:v libx265 -crf {crf} "{output_file}"')
                    #print(222222)
                    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,universal_newlines=True,encoding='utf-8')
                    probe = ffmpeg.probe(input_file)
                    for stream in probe['streams']:
                        #print('stream {0}: {1}'.format(stream['index'], stream['codec_type']))
                        if stream["codec_type"] == 'video':
                            pprint(stream)  # Python3.8からsort_dicts=Falseが使える
                            for line in p.stdout:
                                #self.info.insert(tk.END, f"{line}\n")
                                if line[:7] == "frame= ":
                                    idx = line.find("fps=")
                                    frame = line[:idx].replace(' ', '')
                                    frame = int(frame.replace('frame=', ''))
                                    #print(frame)
                                    #print(stream['nb_frames'])
                                    #print(stream['duration_ts'])
                                    total = int(stream['nb_frames'])
                                    pow = (frame/total)*100.0
                                    #print(f"進捗:{pow}%")
                                    self.progress_var.set(pow)
                                    if pow != 100:
                                        self.label3["text"] = f"{base_filename}\n圧縮中:{pow}%"
                                        print(f"{base_filename}\n圧縮中:{pow}%")
                                    if pow == 100:
                                        self.label3["text"] = f"{base_filename}\n圧縮完了"
                                        print(f"{base_filename}\n圧縮完了")

                    try:
                        outs, errs = p.communicate()
                    except subprocess.TimeoutExpired:
                        pass
                    else:
                        p.terminate()

            except Exception as error:
                print(error.args)
                messagebox.showinfo("動画ファイル圧縮エラー", "動画ファイル圧縮中にエラーが発生しました。")
                return

    messagebox.showinfo("動画ファイル圧縮終了", "動画ファイルの圧縮が終わりました。")


    # -------------------------------------------------------------------------#

if __name__ == "__main__":
    global root
    root = TkinterDnD.Tk()
    app = Application(master=root)
    app.mainloop()