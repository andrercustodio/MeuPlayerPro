import flet as ft
import yt_dlp
import time
import threading
import traceback

# --- CLASSE DE LÓGICA (O "CÉREBRO" DO APP) ---
class AudioController:
    def __init__(self, page):
        self.page = page
        self.playlist = []
        self.current_index = 0
        self.is_playing = False
        self.audio_widget = self._criar_audio_widget()
        
        # Injeta o audio na página (Overlay)
        if self.audio_widget:
            self.page.overlay.append(self.audio_widget)
            # REMOVIDO: self.page.update() 
            # (Não atualizamos a página aqui para evitar erro de inicialização)

    def _criar_audio_widget(self):
        try:
            # Verifica se o componente Audio existe no Flet atual
            if not hasattr(ft, "Audio"):
                return None
                
            return ft.Audio(
                autoplay=False,
                volume=1.0,
                on_position_changed=self._on_position_change,
                on_state_changed=self._on_state_change
            )
        except:
            return None

    def _on_position_change(self, e):
        # Envia atualização apenas se a página estiver ativa
        if self.page:
            self.page.pubsub.send_all({"tipo": "progresso", "ms": int(e.data)})

    def _on_state_change(self, e):
        if e.data == "completed":
            self.proxima()

    def carregar_audio(self, url):
        if self.audio_widget:
            self.audio_widget.src = url
            self.audio_widget.update()
            
    def play(self):
        if self.audio_widget:
            self.audio_widget.play()
            self.is_playing = True

    def pause(self):
        if self.audio_widget:
            self.audio_widget.pause()
            self.is_playing = False
            
    def resume(self):
        if self.audio_widget:
            self.audio_widget.resume()
            self.is_playing = True

    def seek(self, ms):
        if self.audio_widget:
            self.audio_widget.seek(int(ms))

    def proxima(self):
        if self.current_index + 1 < len(self.playlist):
            self.tocar_index(self.current_index + 1)
        else:
            self.page.pubsub.send_all({"tipo": "status", "texto": "Fim da Playlist"})

    def anterior(self):
        if self.current_index > 0:
            self.tocar_index(self.current_index - 1)

    def tocar_index(self, index):
        if not self.playlist or index < 0 or index >= len(self.playlist): return
        
        self.current_index = index
        musica_raw = self.playlist[index]
        
        try:
            titulo = musica_raw.split(" - ", 1)[1] if " - " in musica_raw else "Áudio"
        except: titulo = "Áudio"

        self.page.pubsub.send_all({
            "tipo": "mudanca_faixa", 
            "index": index, 
            "titulo": titulo
        })

        threading.Thread(target=self._obter_link_real, args=(musica_raw,), daemon=True).start()

    def _obter_link_real(self, musica_raw):
        link_youtube = musica_raw.split(" - ")[0]
        try:
            ydl_opts = {
                'format': 'bestaudio',
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'noplaylist': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link_youtube, download=False)
                url_stream = info['url']
                capa = info.get('thumbnail', "")
                
                self.carregar_audio(url_stream)
                time.sleep(0.2)
                self.play()
                
                self.page.pubsub.send_all({"tipo": "capa", "src": capa})
                self.page.pubsub.send_all({"tipo": "status", "texto": "Tocando 🎵"})
                
        except Exception as e:
            print(e)
            self.page.pubsub.send_all({"tipo": "status", "texto": "Erro ao carregar. Pulando..."})
            time.sleep(1)
            self.proxima()

    def adicionar_musicas(self, lista_novas):
        self.playlist.extend(lista_novas)
        try:
            self.page.client_storage.set("playlist_v2", self.playlist)
        except: pass

    def carregar_memoria(self):
        try:
            salvo = self.page.client_storage.get("playlist_v2")
            if salvo: self.playlist = salvo
        except: pass

# --- UI (INTERFACE VISUAL) ---
class PlayerUI(ft.Column):
    def __init__(self, page):
        super().__init__()
        self.pg = page 
        self.expand = True 
        self.controller = AudioController(self.pg)
        
        self.pg.pubsub.subscribe(self.on_message)

        # Imagem com correção de segurança para evitar erro ImageFit
        self.img_capa = ft.Image(
            src="https://img.icons8.com/fluency/240/music-record.png", 
            width=140, height=140, 
            border_radius=10, 
            fit="cover" 
        )
        
        self.lbl_titulo = ft.Text("Selecione uma música", size=16, weight="bold", text_align="center")
        self.lbl_status = ft.Text("Aguardando", size=12, color="grey", text_align="center")
        self.lbl_tempo = ft.Text("00:00", size=10)
        self.slider = ft.Slider(min=0, max=100, expand=True, height=20, on_change=lambda e: self.controller.seek(e.control.value))
        
        self.txt_url = ft.TextField(hint_text="Link YouTube", text_size=12, expand=True, height=45, border_radius=10, bgcolor="#222222", border_width=0)
        self.btn_import = ft.IconButton(ft.Icons.DOWNLOAD_ROUNDED, icon_color="blue", bgcolor="#222222", on_click=self.acao_importar)
        
        self.btn_prev = ft.IconButton(ft.Icons.SKIP_PREVIOUS_ROUNDED, icon_size=30, on_click=lambda e: self.controller.anterior())
        self.btn_play = ft.IconButton(ft.Icons.PLAY_CIRCLE_FILLED_ROUNDED, icon_size=60, icon_color="blue", on_click=self.acao_play_pause)
        self.btn_next = ft.IconButton(ft.Icons.SKIP_NEXT_ROUNDED, icon_size=30, on_click=lambda e: self.controller.proxima())
        
        self.lista_view = ft.Column(spacing=2, scroll="auto")
        self.container_lista = ft.Container(content=self.lista_view, expand=True, bgcolor="#0A0A0A", border_radius=15, padding=10)

        self.controls = [
            ft.Container(height=10),
            ft.Text("PLAYER PRO V3", size=12, weight="bold", color="blue", text_align="center"),
            
            ft.Container(
                content=ft.Row([self.txt_url, self.btn_import]),
                padding=10
            ),
            
            ft.Container(
                content=ft.Column([
                    ft.Row([self.img_capa], alignment="center"),
                    ft.Container(height=5),
                    self.lbl_titulo,
                    self.lbl_status,
                    ft.Row([self.lbl_tempo, self.slider], alignment="center"),
                    ft.Row([self.btn_prev, self.btn_play, self.btn_next], alignment="center"),
                ]),
                padding=15,
                bgcolor="#161616",
                border_radius=20,
                margin=10
            ),
            
            ft.Divider(height=1, color="#333333"),
            
            ft.Text("  Sua Playlist:", size=12, color="grey"),
            self.container_lista
        ]

        # Carregar dados
        self.controller.carregar_memoria()
        self.renderizar_lista()

    def on_message(self, message):
        # SEGURANÇA: Se o componente não estiver na tela, para aqui.
        if not self.slider.page: return

        tipo = message.get("tipo")
        
        if tipo == "progresso":
            ms = message["ms"]
            self.slider.value = ms
            self.lbl_tempo.value = time.strftime('%M:%S', time.gmtime(ms // 1000))
            if self.slider.max == 100 and self.controller.audio_widget:
                try:
                    d = self.controller.audio_widget.get_duration()
                    if d: self.slider.max = d
                except: pass
            self.update()
            
        elif tipo == "mudanca_faixa":
            self.lbl_titulo.value = message["titulo"]
            self.btn_play.icon = ft.Icons.PAUSE_CIRCLE_FILLED
            self.lbl_status.value = "Carregando..."
            self.renderizar_lista()
            self.update()
            
        elif tipo == "capa":
            self.img_capa.src = message["src"]
            self.img_capa.update()

        elif tipo == "status":
            self.lbl_status.value = message["texto"]
            self.lbl_status.update()

    def renderizar_lista(self):
        self.lista_view.controls.clear()
        if not self.controller.playlist:
            self.lista_view.controls.append(ft.Text("Lista Vazia", color="grey", text_align="center"))
        
        for i, item in enumerate(self.controller.playlist):
            try:
                titulo = item.split(" - ", 1)[1] if " - " in item else item
            except: titulo = item
            
            eh_atual = (i == self.controller.current_index)
            
            item_ui = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.EQUALIZER if eh_atual else ft.Icons.MUSIC_NOTE, 
                           color="green" if eh_atual else "grey", size=16),
                    ft.Text(f"{i+1}. {titulo}", 
                           color="green" if eh_atual else "white", 
                           size=13, no_wrap=True, overflow="ellipsis", expand=True),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="red", icon_size=16, 
                                 on_click=lambda e, x=i: self.remover_item(x))
                ]),
                padding=10,
                bgcolor="#1A1A1A" if not eh_atual else "#112211",
                border_radius=8,
                on_click=lambda e, x=i: self.controller.tocar_index(x)
            )
            self.lista_view.controls.append(item_ui)
        
        # --- SEGURANÇA CRÍTICA ---
        # Só atualiza a lista se ela JÁ estiver desenhada na tela
        if self.lista_view.page:
            self.lista_view.update()

    def remover_item(self, index):
        if 0 <= index < len(self.controller.playlist):
            self.controller.playlist.pop(index)
            self.controller.page.client_storage.set("playlist_v2", self.controller.playlist)
            self.renderizar_lista()

    def acao_play_pause(self, e):
        if self.controller.is_playing:
            self.controller.pause()
            self.btn_play.icon = ft.Icons.PLAY_CIRCLE_FILLED
        else:
            if self.controller.audio_widget and self.controller.audio_widget.src:
                self.controller.resume()
                self.btn_play.icon = ft.Icons.PAUSE_CIRCLE_FILLED
            else:
                self.controller.tocar_index(self.controller.current_index)
        self.update()

    def acao_importar(self, e):
        url = self.txt_url.value
        if not url: return
        
        self.btn_import.disabled = True
        self.lbl_status.value = "Buscando..."
        self.update()

        def tarefa_bg():
            try:
                opts = {'extract_flat': True, 'quiet': True, 'ignoreerrors': True}
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    novas = []
                    if 'entries' in info:
                        for v in info['entries']:
                            if v: novas.append(f"https://www.youtube.com/watch?v={v['id']} - {v['title']}")
                    else:
                        novas.append(f"{info.get('webpage_url')} - {info.get('title')}")
                    
                    self.controller.adicionar_musicas(novas)
                    
                    # Como roda em background, aqui a página já existe, então o update funciona
                    self.renderizar_lista()
                    self.pg.pubsub.send_all({"tipo": "status", "texto": f"{len(novas)} adicionadas!"})
            except Exception as err:
                self.pg.pubsub.send_all({"tipo": "status", "texto": "Erro ao buscar link"})
            
            self.btn_import.disabled = False
            self.txt_url.value = ""
            if self.txt_url.page: self.update()

        threading.Thread(target=tarefa_bg, daemon=True).start()

def main(page: ft.Page):
    page.title = "Player Pro"
    page.bgcolor = "black"
    page.theme_mode = "dark"
    page.padding = 0
    page.window_width = 390
    page.window_height = 800
    
    try:
        app = PlayerUI(page)
        page.add(app)
    except Exception as e:
        page.add(ft.Text(f"Erro Fatal: {e}", color="red"))

if __name__ == "__main__":
    ft.app(target=main)
