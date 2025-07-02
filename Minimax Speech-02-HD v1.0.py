import os
import sys
import threading
import requests
import customtkinter as ctk
from tkinter import filedialog
import pygame
import time
import shutil
import json
import replicate

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))

    return os.path.join(base_path, relative_path)

class LanguageManager:
    def __init__(self, language_folder="langs", default_lang="en_US"):
        self.language_folder = resource_path(language_folder)
        
        self.languages = {}
        self.current_lang_data = {}
        self._discover_languages()
        
        default_display_name = "English"
        for display_name, code in self.languages.items():
            if code == default_lang:
                default_display_name = display_name 
                break
        self.set_language(default_display_name)

    def _discover_languages(self):
        try:
            for filename in os.listdir(self.language_folder):
                if filename.endswith(".json"):
                    lang_code = filename.split(".")[0]
                    try:
                        with open(os.path.join(self.language_folder, filename), 'r', encoding='utf-8') as f:
                            display_name = json.load(f).get("language_display_name", lang_code)
                            self.languages[display_name] = lang_code
                    except (json.JSONDecodeError, KeyError) as e:
                        print(f"警告: 无法解析语言文件 {filename}: {e}")
        except FileNotFoundError:
            print(f"错误：找不到语言文件夹 '{self.language_folder}'。")
            self.languages = {"English": "en_US"}

    def get_available_languages(self):
        return list(self.languages.keys())

    def set_language(self, lang_display_name):
        lang_code = self.languages.get(lang_display_name, "en_US")
        filepath = os.path.join(self.language_folder, f"{lang_code}.json")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.current_lang_data = json.load(f)
                print(f"已加载语言: {lang_display_name}")
        except FileNotFoundError:
            print(f"错误：找不到语言文件 '{filepath}'。")
            self.current_lang_data = {}

    def get(self, key, default_value=None):
        if default_value is None:
            default_value = {} if isinstance(key, list) else ""
        return self.current_lang_data.get(key, default_value)


class SpeechApp(ctk.CTk):
    
    PARAMETER_CONFIG = [
        {"id": "voice_id",      "type": "combobox", "json_map": "voice_map"},
        {"id": "speed",         "type": "slider",   "range": (0.5, 2.0), "steps": 30,  "default": 1.0},
        {"id": "volume",        "type": "slider",   "range": (0.0, 10.0),"steps": 100, "default": 1.0},
        {"id": "pitch",         "type": "slider",   "range": (-12, 12),  "steps": 24,  "default": 0},
        {"id": "emotion",       "type": "combobox", "json_map": "emotion_map"},
        {"id": "eng_norm",      "type": "checkbox", "default": False},
        {"id": "advanced_sep",  "type": "separator"},
        {"id": "bitrate",       "type": "combobox", "options": ["32000", "64000", "128000", "256000"], "default": "128000"},
        {"id": "sample_rate",   "type": "combobox", "options": ["8000", "16000", "22050", "24000", "32000", "44100"], "default": "32000"},
        {"id": "channel",       "type": "combobox", "json_map": "channel_map"},
        {"id": "lang_boost",    "type": "combobox", "json_map": "language_boost_map"},
    ]

    def __init__(self):
        super().__init__()
        
        self.lang_manager = LanguageManager()

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        self.geometry("1000x750")
        
        try:
            icon_path = resource_path("favicon.ico")
            self.iconbitmap(icon_path)
        except Exception as e:
            print(f"设置图标失败: {e}")


        pygame.mixer.init()
        self.temp_audio_path = None
        self.placeholder_color = 'gray50'
        self.default_text_color = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.param_widgets = {}
        self.param_vars = {}
        self.custom_voice_id_var = ctk.StringVar(value="")

        self.create_main_layout()
        self.create_widgets()
        self.update_ui_language()

    def create_main_layout(self):
        self.left_frame = ctk.CTkFrame(self, corner_radius=10)
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.left_frame.grid_columnconfigure(0, weight=1)

        self.right_frame = ctk.CTkFrame(self, corner_radius=10)
        self.right_frame.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(2, weight=1)

    def create_widgets(self):
        self.api_frame = ctk.CTkFrame(self.left_frame)
        self.api_frame.pack(pady=10, padx=10, fill="x")
        self.api_frame.grid_columnconfigure(1, weight=1)
        self.api_key_label = ctk.CTkLabel(self.api_frame, text="")
        self.api_key_label.grid(row=0, column=0, padx=(10, 5))
        self.api_key_entry = ctk.CTkEntry(self.api_frame, show="*")
        self.api_key_entry.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")

        self.text_label = ctk.CTkLabel(self.left_frame, text="", font=ctk.CTkFont(weight="bold"))
        self.text_label.pack(padx=10, pady=(10, 0), anchor="w")
        self.text_input = ctk.CTkTextbox(self.left_frame, height=150, corner_radius=8)
        self.text_input.pack(pady=10, padx=10, fill="x", expand=True)
        self.default_text_color = self.text_input.cget("text_color")
        self.text_input.bind("<FocusIn>", self.on_textbox_focus_in)
        self.text_input.bind("<FocusOut>", self.on_textbox_focus_out)

        self.params_frame = ctk.CTkFrame(self.left_frame)
        self.params_frame.pack(pady=10, padx=10, fill="both", expand=True)
        self.params_frame.grid_columnconfigure(1, weight=1)
        self.create_parameter_controls(self.params_frame)

        lang_frame = ctk.CTkFrame(self.right_frame)
        lang_frame.pack(pady=(10, 0), padx=10, fill="x")
        self.lang_label = ctk.CTkLabel(lang_frame, text="Language:")
        self.lang_label.pack(side="left", padx=(10, 5))
        
        self.lang_var = ctk.StringVar(value=self.lang_manager.get("language_display_name"))
        self.lang_menu = ctk.CTkComboBox(lang_frame, 
                                         values=self.lang_manager.get_available_languages(),
                                         variable=self.lang_var, 
                                         command=self.on_language_change)
        self.lang_menu.pack(side="left", expand=True, fill="x", padx=(0, 10))

        self.generate_button = ctk.CTkButton(self.right_frame, text="", command=self.start_generation_thread, height=40, font=ctk.CTkFont(size=16, weight="bold"))
        self.generate_button.pack(pady=10, padx=10, fill="x")

        self.log_label = ctk.CTkLabel(self.right_frame, text="", font=ctk.CTkFont(weight="bold"))
        self.log_label.pack(padx=10, pady=(10, 0), anchor="w")
        self.log_textbox = ctk.CTkTextbox(self.right_frame, corner_radius=8, state="disabled", text_color="gray")
        self.log_textbox.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.audio_control_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.audio_control_frame.pack(pady=10, padx=10, fill="x")
        self.audio_control_frame.grid_columnconfigure((0, 1), weight=1)
        self.play_button = ctk.CTkButton(self.audio_control_frame, text="", command=self.play_audio, state="disabled")
        self.play_button.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        self.save_button = ctk.CTkButton(self.audio_control_frame, text="", command=self.save_audio, state="disabled")
        self.save_button.grid(row=0, column=1, padx=(5, 0), sticky="ew")

    def create_parameter_controls(self, parent_frame):
        row_counter = 0
        for config in self.PARAMETER_CONFIG:
            param_id = config["id"]
            control_type = config["type"]
            
            if control_type == "slider":
                self.param_vars[param_id] = ctk.DoubleVar(value=config.get("default", 0))
            elif control_type == "checkbox":
                self.param_vars[param_id] = ctk.BooleanVar(value=config.get("default", False))
            else:
                self.param_vars[param_id] = ctk.StringVar(value=config.get("default", ""))

            label = ctk.CTkLabel(parent_frame, text="")
            self.param_widgets[param_id] = {'label': label}

            if control_type == "separator":
                label.grid(row=row_counter, column=0, columnspan=2, pady=10)
                label.configure(font=ctk.CTkFont(slant="italic"))
                row_counter += 1
                continue

            label.grid(row=row_counter, column=0, padx=10, pady=5, sticky="w")
            
            if control_type == "slider":
                control = ctk.CTkSlider(parent_frame, 
                                        from_=config["range"][0], 
                                        to=config["range"][1],
                                        number_of_steps=config["steps"],
                                        variable=self.param_vars[param_id])
            elif control_type == "checkbox":
                control = ctk.CTkCheckBox(parent_frame, text="", variable=self.param_vars[param_id])
                label.grid_remove()
            elif control_type == "combobox":
                control = ctk.CTkComboBox(parent_frame, 
                                          values=config.get("options", []), 
                                          variable=self.param_vars[param_id])
                if param_id == "voice_id":
                    control.configure(command=self.on_voice_id_change)
                    self.param_widgets[param_id]['control'] = control
                    control.grid(row=row_counter, column=1, padx=10, pady=5, sticky="ew")

                    self.custom_voice_id_entry = ctk.CTkEntry(parent_frame, 
                                                            textvariable=self.custom_voice_id_var,
                                                            placeholder_text="Enter custom voice ID")
                    self.custom_voice_id_entry.grid(row=row_counter + 1, column=1, padx=10, pady=5, sticky="ew")
                    self.custom_voice_id_entry.grid_remove() 
                    
                    row_counter += 1 
            else: 
                 control = ctk.CTkComboBox(parent_frame, 
                                          values=config.get("options", []), 
                                          variable=self.param_vars[param_id])


            if param_id != "voice_id" or control_type != "combobox":
                control.grid(row=row_counter, column=1 if control_type != "checkbox" else 0, 
                            columnspan=1 if control_type != "checkbox" else 2,
                            padx=10, pady=5 if control_type != "checkbox" else 10, 
                            sticky="ew")
                self.param_widgets[param_id]['control'] = control
            row_counter += 1

    def on_voice_id_change(self, choice):
        lm = self.lang_manager
        if "voice_custom_option" in lm.current_lang_data and choice == lm.get("voice_custom_option"):
            self.custom_voice_id_entry.grid() 
            self.custom_voice_id_entry.configure(state="normal")
        else:
            self.custom_voice_id_entry.grid_remove() 
            self.custom_voice_id_entry.configure(state="disabled")
            self.custom_voice_id_var.set("") 


    def on_language_change(self, choice):
        self.lang_manager.set_language(choice)
        self.update_ui_language()

    def update_ui_language(self):
        lm = self.lang_manager
        self.title(lm.get("window_title"))
        
        self.api_key_label.configure(text=lm.get("api_key_label"))
        self.api_key_entry.configure(placeholder_text=lm.get("api_key_placeholder"))
        self.text_label.configure(text=lm.get("text_input_label"))
        self.on_textbox_focus_out(None)
        
        for config in self.PARAMETER_CONFIG:
            param_id = config["id"]
            widgets = self.param_widgets[param_id]
            
            label_key = f"param_{param_id.replace('_sep', '_settings')}"
            if 'label' in widgets:
                widgets['label'].configure(text=lm.get(label_key))
            if config["type"] == "checkbox":
                widgets['control'].configure(text=lm.get(label_key))
            
            if "json_map" in config:
                json_key = config["json_map"]
                options_map = lm.get(json_key, {})
                options_display = list(options_map.keys())
                
                if param_id == "voice_id" and "voice_custom_option" in lm.current_lang_data:
                    options_display.insert(0, lm.get("voice_custom_option"))
                    self.custom_voice_id_entry.configure(placeholder_text=lm.get("custom_voice_id_placeholder"))


                widgets['control'].configure(values=options_display)
                if options_display:
                    current_value = self.param_vars[param_id].get()
                    if current_value not in options_display and self.custom_voice_id_var.get() == "":
                        self.param_vars[param_id].set(options_display[0])


        self.lang_label.configure(text=lm.get("language_label"))
        self.generate_button.configure(text=lm.get("generate_button"))
        self.log_label.configure(text=lm.get("log_label"))
        self.play_button.configure(text=lm.get("play_button"))
        self.save_button.configure(text=lm.get("save_button"))
        
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_message(lm.get("welcome_log"))
        self.log_textbox.configure(state="disabled")
        
        self.on_voice_id_change(self.param_vars["voice_id"].get())


    def on_textbox_focus_in(self, event):
        if self.text_input.get("1.0", "end-1c").strip() == self.lang_manager.get("text_input_placeholder"):
            self.text_input.delete("1.0", "end")
            self.text_input.configure(text_color=self.default_text_color)

    def on_textbox_focus_out(self, event):
        if not self.text_input.get("1.0", "end-1c").strip():
            self.text_input.delete("1.0", "end")
            self.text_input.insert("0.0", self.lang_manager.get("text_input_placeholder"))
            self.text_input.configure(text_color=self.placeholder_color)

    def log_message(self, message):
        def _update_log():
            self.log_textbox.configure(state="normal")
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            self.log_textbox.insert("end", f"[{timestamp}] {message}\n")
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
        self.after(0, _update_log)

    def set_ui_state(self, is_generating):
        state = "disabled" if is_generating else "normal"
        self.generate_button.configure(state=state, text=self.lang_manager.get("generating_button") if is_generating else self.lang_manager.get("generate_button"))
        self.lang_menu.configure(state=state)

        for param_id, widgets in self.param_widgets.items():
            if 'control' in widgets: 
                widgets['control'].configure(state=state)
        
        if "voice_custom_option" in self.lang_manager.current_lang_data and self.param_vars["voice_id"].get() == self.lang_manager.get("voice_custom_option"):
            self.custom_voice_id_entry.configure(state=state)
        else:
            self.custom_voice_id_entry.configure(state="disabled")


        self.api_key_entry.configure(state=state)
        self.text_input.configure(state=state)

        if is_generating:
            self.play_button.configure(state="disabled")
            self.save_button.configure(state="disabled")

    def start_generation_thread(self):
        lm = self.lang_manager
        if self.temp_audio_path and os.path.exists(self.temp_audio_path):
            try:
                pygame.mixer.music.unload()
                time.sleep(0.1)
                os.remove(self.temp_audio_path)
                self.temp_audio_path = None
                self.log_message(lm.get("log_cleaned_temp"))
            except Exception as e:
                self.log_message(f"{lm.get('log_clean_failed')}: {e}")
        
        self.set_ui_state(True)
        self.log_message(lm.get("log_task_start"))
        
        threading.Thread(target=self.run_generation, daemon=True).start()

    def run_generation(self):
        lm = self.lang_manager
        try:
            api_key = self.api_key_entry.get()
            if not api_key: raise ValueError(lm.get("error_no_api_key"))
            
            text_content = self.text_input.get("1.0", "end-1c")
            if text_content.strip() == lm.get("text_input_placeholder") or not text_content.strip():
                raise ValueError(lm.get("error_no_text"))
            if len(text_content) > 5000:
                raise ValueError(f"{lm.get('error_text_too_long')} ({len(text_content)}/5000)！")

            os.environ["REPLICATE_API_TOKEN"] = api_key
            
            self.log_message(lm.get("log_collecting_params"))
            
            params = {"text": text_content}
            for config in self.PARAMETER_CONFIG:
                param_id = config["id"]
                if config["type"] == "separator":
                    continue

                raw_value = self.param_vars[param_id].get()

                if param_id == 'eng_norm':
                    api_param_id = 'english_normalization'
                elif param_id == 'lang_boost':
                    api_param_id = 'language_boost'
                else:
                    api_param_id = param_id

                if config["type"] == "checkbox":
                    params[api_param_id] = raw_value
                elif config["type"] == "slider":
                    params[api_param_id] = int(raw_value) if param_id == "pitch" else raw_value
                elif config["type"] == "combobox":
                    if param_id == "voice_id" and "voice_custom_option" in lm.current_lang_data:
                        if raw_value == lm.get("voice_custom_option"):
                            custom_id = self.custom_voice_id_var.get().strip()
                            if not custom_id:
                                raise ValueError(lm.get("error_custom_voice_id_empty"))
                            params[api_param_id] = custom_id
                        else:
                            json_key = config["json_map"]
                            options_map = lm.get(json_key, {})
                            params[api_param_id] = options_map.get(raw_value, raw_value)
                    else: 
                        if "json_map" in config:
                            json_key = config["json_map"]
                            options_map = lm.get(json_key, {})
                            params[api_param_id] = options_map.get(raw_value, raw_value)
                        else:
                            params[api_param_id] = int(raw_value) if raw_value.isdigit() else raw_value
            
            final_voice_id = params.get('voice_id', 'N/A')
            self.log_message(f"{lm.get('log_using_voice')}: {final_voice_id}")
            if 'language_boost' in params and params['language_boost'] != 'None':
                 self.log_message(f"Using language boost: {params['language_boost']}")

            self.log_message(lm.get("log_calling_api"))
            output_url = replicate.run("minimax/speech-02-hd", input=params)
            self.log_message(lm.get("log_api_success"))

            response = requests.get(output_url, stream=True)
            response.raise_for_status()

            temp_dir = os.path.join(os.path.dirname(resource_path('.')), "temp_audio")
            os.makedirs(temp_dir, exist_ok=True)
            self.temp_audio_path = os.path.join(temp_dir, "temp_output.mp3")

            with open(self.temp_audio_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
            self.log_message(lm.get("log_download_complete"))

            self.after(0, lambda: self.play_button.configure(state="normal"))
            self.after(0, lambda: self.save_button.configure(state="normal"))

        except Exception as e:
            self.log_message(f"{lm.get('error_generic')}: {str(e)}")
        finally:
            self.after(0, lambda: self.set_ui_state(False))

    def play_audio(self):
        lm = self.lang_manager
        if self.temp_audio_path and os.path.exists(self.temp_audio_path):
            try:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop(); pygame.mixer.music.unload() 
                    self.play_button.configure(text=lm.get("play_button"))
                else:
                    pygame.mixer.music.load(self.temp_audio_path)
                    pygame.mixer.music.play()
                    self.log_message(lm.get("log_playing"))
                    self.play_button.configure(text=lm.get("stop_button"))
                    self.check_if_playing()
            except pygame.error as e:
                self.log_message(f"{lm.get('error_playback_failed')}: {e}")
        else:
            self.log_message(lm.get("error_no_audio_file"))
            
    def check_if_playing(self):
        if pygame.mixer.music.get_busy():
            self.after(100, self.check_if_playing)
        else:
            self.play_button.configure(text=self.lang_manager.get("play_button"))
            self.log_message(self.lang_manager.get("log_playback_finished"))

    def save_audio(self):
        lm = self.lang_manager
        if self.temp_audio_path and os.path.exists(self.temp_audio_path):
            save_path = filedialog.asksaveasfilename(
                defaultextension=".mp3",
                filetypes=[(lm.get("file_dialog_type"), "*.mp3")],
                title=lm.get("file_dialog_title"),
                initialfile="generated_speech.mp3"
            )
            if save_path:
                try:
                    shutil.copy(self.temp_audio_path, save_path)
                    self.log_message(f"{lm.get('log_save_success')}: {save_path}")
                except Exception as e:
                    self.log_message(f"{lm.get('log_save_failed')}: {e}")
        else:
            self.log_message(lm.get("error_no_audio_file"))

    def on_closing(self):
        self.log_message(self.lang_manager.get("log_closing"))
        temp_dir = os.path.join(os.path.dirname(resource_path('.')), "temp_audio")
        if os.path.exists(temp_dir):
            pygame.mixer.quit()
            time.sleep(0.1)
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                print(f"关闭时删除临时目录失败: {e}")
        else:
             pygame.mixer.quit()
        self.destroy()

if __name__ == "__main__":
    app = SpeechApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
