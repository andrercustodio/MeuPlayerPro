import flet as ft
import traceback

def main(page: ft.Page):
    # Configurações de Performance e Compatibilidade
    page.title = "Player Turbo"
    page.bgcolor = "black"
    page.scroll = "auto" 
    page.theme_mode = "dark"
    page.padding = 5
    
    # Reduzir animações para ganhar velocidade
    page.window_width = 390
    page.window_height = 700

    try:
        # --- INÍCIO DO CÓDIGO ---
        import yt_dlp
        import time
        import threading
        import random

        # Variáveis Globais
        all_playlists = {"Principal": []} 
        current_playlist_name = "Principal"
        playlist = [] 
        current_index = 0   
        is_playing = False
        is_shuffled = False
        audio_player = None # Variável do player

        # --- UI Elementos ---
        
        snack_aviso = ft.SnackBar(ft.Text(""), bgcolor="blue")
        page.overlay.append(snack_aviso)

        def mostrar_aviso(texto, cor="blue"):
            snack_aviso.content.value = texto
            snack_aviso.bgcolor = cor
            snack_aviso.open = True
            page.update()
        
        lbl_Andre0 = ft.Text("                          ", color="grey", weight="bold", size=14, text_align="center")
        lbl_nome_playlist = ft.Text(f"Playlist: {current_playlist_name}", size=12, color="blue200", weight="bold")
        lbl_Andre = ft.Text("Player Mobile - André R. Custódio 😜", color="grey", weight="bold", size=14, text_align="center")
        
        txt_import_url = ft.TextField(
            hint_text="Link...", text_size=12, expand=True, height=40, content_padding=10, border_radius=15
        )
        
        # Lista otimizada sem auto_scroll para performance
        lv_playlist = ft.ListView(expand=True, spacing=0, padding=0, auto_scroll=False)

        img_capa = ft.Image(
            src="https://img.icons8.com/fluency/240/music-record.png",
            width=100, height=100, border_radius=5, # Capa menor carrega mais rápido
            fit="cover" 
        )

        lbl_titulo = ft.Text("Pronto", weight="bold", size=13, no_wrap=True, overflow="ellipsis", text_align="center")
        lbl_status = ft.Text("...", size=11, color="grey", text_align="center")
        
        lbl_tempo_now = ft.Text("00:00", size=10)
        
        # --- Lógica de Áudio ---

        def seek_audio(val): 
            try:
                if audio_player: audio_player.seek(int(val))
            except: pass

        slider_tempo = ft.Slider(min=0, max=100, value=0, expand=True, height=20, on_change=lambda e: seek_audio(e.control.value))

        def atualizar_progresso(e):
            # Otimização: Só atualiza se estiver tocando
            if is_playing and audio_player:
                try:
                    ms = int(e.data)
                    slider_tempo.value = ms
                    lbl_tempo_now.value = time.strftime('%M:%S', time.gmtime(ms // 1000))
                    # Duração total não atualizamos toda hora para poupar CPU
                    if slider_tempo.max == 100: # Só ajusta se não tiver ajustado
                        dur = audio_player.get_duration()
                        if dur: slider_tempo.max = dur
                except: pass
                page.update()
        
        def verificar_fim(e):
            if e.data == "completed": proxima(None)

        # Inicialização do Audio Player
        try:
            if hasattr(ft, 'Audio'):
                audio_player = ft.Audio(
                    src="https://luan.xyz/files/audio/ambient_c_motion.mp3", 
                    autoplay=False, volume=1.0,
                    on_position_changed=lambda e: atualizar_progresso(e),
                    on_state_changed=lambda e: verificar_fim(e)
                )
                page.overlay.append(audio_player)
        except: pass

        # --- Funções Principais ---

        def renderizar_playlist():
            # OTIMIZAÇÃO: Renderização simplificada
            lv_playlist.controls.clear()
            
            if not playlist:
                lv_playlist.controls.append(ft.Text("Vazia.", color="grey", size=12))
            else:
                for i, item in enumerate(playlist):
                    # Tenta pegar só o titulo rapido
                    try:
                        titulo = item.split(" - ", 1)[1]
                    except: titulo = item

                    # Se for a musica atual, muda a cor
                    eh_atual = (i == current_index)
                    cor_texto = "green" if eh_atual else "white"
                    icone = ft.Icons.PLAY_ARROW if eh_atual else ft.Icons.MUSIC_NOTE

                    # Layout simplificado (Row simples) carrega mais rápido que Containers aninhados
                    linha = ft.TextButton(
                        content=ft.Row([
                            ft.Icon(icone, size=14, color=cor_texto),
                            ft.Text(f"{i+1}. {titulo}", size=11, color=cor_texto, no_wrap=True, overflow="ellipsis", expand=True),
                            ft.IconButton(ft.Icons.CLOSE, icon_color="red", icon_size=14, on_click=lambda e, x=i: remover_musica(x))
                        ], alignment="spaceBetween"),
                        style=ft.ButtonStyle(padding=5),
                        on_click=lambda e, x=i: tocar_index(x)
                    )
                    lv_playlist.controls.append(linha)
            page.update()

        def salvar_carregar(acao):
            try:
                if acao == "salvar":
                    all_playlists[current_playlist_name] = playlist
                    page.client_storage.set("pl_data", all_playlists)
                    page.client_storage.set("last_pl", current_playlist_name)
                elif acao == "carregar":
                    d = page.client_storage.get("pl_data")
                    l = page.client_storage.get("last_pl")
                    if d: 
                        nonlocal all_playlists, current_playlist_name, playlist
                        all_playlists = d
                        if l and l in all_playlists: current_playlist_name = l
                        else: current_playlist_name = list(all_playlists.keys())[0]
                        playlist = all_playlists[current_playlist_name]
                        lbl_nome_playlist.value = f"Playlist: {current_playlist_name}"
            except: pass

        def importar_link(e):
            url = txt_import_url.value
            if not url: return
            lbl_status.value = "Buscando..."
            btn_import.disabled = True
            page.update()

            def processar():
                nonlocal playlist
                # OTIMIZAÇÃO: 'extract_flat' e 'skip_download' para ser rapido
                opts = {'extract_flat': True, 'quiet': True, 'no_warnings': True, 'ignoreerrors': True}
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        novas = []
                        if 'entries' in info:
                            for v in info['entries']:
                                if v: novas.append(f"https://www.youtube.com/watch?v={v.get('id')} - {v.get('title','Track')}")
                        else:
                            novas.append(f"{info.get('webpage_url', url)} - {info.get('title', 'Track')}")
                        
                        playlist.extend(novas)
                        salvar_carregar("salvar")
                        renderizar_playlist()
                        mostrar_aviso("Adicionado!", "green")
                except: mostrar_aviso("Erro ao buscar", "red")
                
                btn_import.disabled = False
                lbl_status.value = "Pronto"
                txt_import_url.value = ""
                page.update()
            
            threading.Thread(target=processar, daemon=True).start()

        def tocar_index(index):
            nonlocal current_index, is_playing
            if not playlist or index < 0 or index >= len(playlist): return
            
            current_index = index
            renderizar_playlist() # Atualiza visual da lista
            
            raw_item = playlist[current_index]
            link = raw_item.split(" - ")[0]
            nome = raw_item.split(" - ", 1)[1] if " - " in raw_item else "Audio"
            
            lbl_titulo.value = nome
            lbl_status.value = "Carregando Audio..."
            if audio_player: audio_player.pause()
            page.update()

            def extrair_turbo():
                nonlocal is_playing
                if not audio_player: return
                try:
                    # OTIMIZAÇÃO MÁXIMA DO YT_DLP
                    ydl_opts = {
                        'format': 'bestaudio', # Pega qualquer audio bom (não filtra m4a pra ser rapido)
                        'quiet': True,
                        'no_warnings': True,
                        'nocheckcertificate': True, # Ignora SSL (mais rapido)
                        'noplaylist': True,
                        'socket_timeout': 10 # Desiste se a net travar
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(link, download=False)
                        url_play = info['url']
                        
                        audio_player.src = url_play
                        if info.get('thumbnail'): img_capa.src = info['thumbnail']
                        
                        audio_player.update()
                        # Sleep reduzido de 0.5 para 0.1
                        time.sleep(0.1) 
                        audio_player.play()
                        
                        is_playing = True
                        lbl_status.value = "Tocando 🔊"
                        btn_play.icon = ft.Icons.PAUSE_CIRCLE_FILLED
                except Exception as e:
                    print(e)
                    mostrar_aviso("Falha no link. Pulando...", "orange")
                    time.sleep(1)
                    proxima(None)
                page.update()

            threading.Thread(target=extrair_turbo, daemon=True).start()

        def controles(acao):
            nonlocal is_playing, current_index, is_shuffled
            if acao == "play":
                if not audio_player: return
                if is_playing:
                    audio_player.pause()
                    is_playing = False
                    btn_play.icon = ft.Icons.PLAY_CIRCLE_FILLED
                else:
                    if audio_player.src: 
                        audio_player.resume()
                        is_playing = True
                        btn_play.icon = ft.Icons.PAUSE_CIRCLE_FILLED
                    else: tocar_index(current_index)
            
            elif acao == "next":
                if current_index + 1 < len(playlist): tocar_index(current_index + 1)
            
            elif acao == "prev":
                if current_index > 0: tocar_index(current_index - 1)
            
            elif acao == "shuffle":
                is_shuffled = not is_shuffled
                if is_shuffled: 
                    random.shuffle(playlist)
                    mostrar_aviso("Aleatório ON")
                else: mostrar_aviso("Aleatório OFF")
                renderizar_playlist()
                salvar_carregar("salvar")

            page.update()

        def remover_musica(idx):
            if 0 <= idx < len(playlist):
                playlist.pop(idx)
                salvar_carregar("salvar")
                renderizar_playlist()

        # --- Montagem Simples (Menos aninhamento = Mais FPS) ---
        
        btn_import = ft.IconButton(ft.Icons.DOWNLOAD, on_click=importar_link, icon_color="blue")
        
        # Botoes de controle compactos
        btn_prev = ft.IconButton(ft.Icons.SKIP_PREVIOUS, on_click=lambda e: controles("prev"))
        btn_play = ft.IconButton(ft.Icons.PLAY_CIRCLE_FILLED, icon_size=50, icon_color="blue", on_click=lambda e: controles("play"))
        btn_next = ft.IconButton(ft.Icons.SKIP_NEXT, on_click=lambda e: controles("next"))
        btn_shuffle = ft.IconButton(ft.Icons.SHUFFLE, icon_size=20, on_click=lambda e: controles("shuffle"))

        # Menu simplificado antigo
        btn_menu = ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT,
            items=[
                ft.PopupMenuItem(content=ft.Text("Limpar Playlist"), on_click=lambda e: limpar_tudo()),
            ]
        )
        def limpar_tudo():
            nonlocal playlist
            playlist = []
            renderizar_playlist()
            salvar_carregar("salvar")

        # Adicionar elementos na página
        page.add(
            ft.Column([
                ft.Row([lbl_Andre0], alignment="center"),
                ft.Row([lbl_Andre], alignment="center"),
                ft.Row([txt_import_url, btn_import], alignment="center"),
                ft.Row([lbl_nome_playlist], alignment="center"),
                ft.Divider(height=1, color="#333333"),
                
                # Area do Player
                ft.Row([
                    img_capa,
                    ft.Column([
                        lbl_titulo,
                        lbl_status,
                        lbl_tempo_now,
                        slider_tempo
                    ], expand=True)
                ], alignment="start"),

                ft.Row([btn_shuffle, btn_prev, btn_play, btn_next, btn_menu], alignment="center"),
                
                ft.Divider(height=1, color="#333333"),
                
                # Lista expandida
                ft.Container(content=lv_playlist, expand=True, bgcolor="#111111", border_radius=5)
            ], expand=True)
        )

        salvar_carregar("carregar")
        renderizar_playlist()

        # --- FIM DO CÓDIGO ---

    except Exception as e:
        page.clean()
        page.add(ft.Text(f"Erro: {e}", color="red"))
        page.update()

ft.app(target=main)
