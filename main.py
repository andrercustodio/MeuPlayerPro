import flet as ft
import traceback

def main(page: ft.Page):
    # Configuração inicial "blindada" para versões antigas
    page.title = "Player Mobile"
    page.bgcolor = "black"
    # Proteção: scroll como string
    page.scroll = "auto" 

    try:
        # --- AQUI COMEÇA O SEU CÓDIGO (DENTRO DA PROTEÇÃO) ---
        
        # 1. Importações
        import yt_dlp
        import time
        import threading
        import random

        # --- 2. Configurações da Janela ---
        page.window_width = 390
        page.window_height = 700
        page.theme_mode = "dark"
        page.padding = 5
        
        # --- 3. Variáveis de Estado Globais ---
        all_playlists = {"Principal": []} 
        current_playlist_name = "Principal"
        
        playlist = [] 
        current_index = 0   
        is_playing = False
        is_shuffled = False

        # --- 4. Componentes da UI ---
        
        snack_aviso = ft.SnackBar(ft.Text(""), bgcolor="blue")
        page.overlay.append(snack_aviso)

        def mostrar_aviso(texto, cor="blue"):
            snack_aviso.content.value = texto
            snack_aviso.bgcolor = cor
            snack_aviso.open = True
            page.update()

        lbl_Andre = ft.Text("Player Mobile - André R. Custódio 😜", color="grey", weight="bold", size=14, text_align="center")
        
        lbl_nome_playlist = ft.Text(f"Playlist: {current_playlist_name}", size=12, color="blue200", weight="bold")

        txt_import_url = ft.TextField(
            hint_text="Link do YouTube...", 
            text_size=12, expand=True, height=40, content_padding=10, border_radius=20
        )
        
        # Proteção: auto_scroll falso e sem enum
        lv_playlist = ft.ListView(expand=True, spacing=2, padding=5, auto_scroll=False)

        # Proteção: fit="cover" como string
        img_capa = ft.Image(
            src="https://img.icons8.com/fluency/240/music-record.png",
            width=130, height=130, border_radius=10, 
            fit="cover" 
        )

        lbl_titulo = ft.Text("Selecione ou Importe", weight="bold", size=14, no_wrap=True, overflow="ellipsis", text_align="center")
        lbl_status = ft.Text("Parado", size=11, color="grey", text_align="center")
        
        lbl_tempo_now = ft.Text("00:00", size=10)
        lbl_tempo_total = ft.Text("--:--", size=10)
        
        # --- SISTEMA DE ÁUDIO SEGURO ---
        # Variável global para o player
        audio_player = None

        def seek_audio(val): 
            try:
                if audio_player:
                    audio_player.seek(int(val))
            except: pass

        slider_tempo = ft.Slider(min=0, max=100, value=0, expand=True, height=10, on_change=lambda e: seek_audio(e.control.value))

        def atualizar_progresso(e):
            if is_playing and audio_player:
                try:
                    ms = int(e.data)
                    slider_tempo.value = ms
                    lbl_tempo_now.value = time.strftime('%M:%S', time.gmtime(ms // 1000))
                    dur = audio_player.get_duration()
                    if dur: 
                        slider_tempo.max = dur
                        lbl_tempo_total.value = time.strftime('%M:%S', time.gmtime(dur // 1000))
                except: pass
                page.update()
        
        def verificar_fim(e):
            if e.data == "completed": proxima(None)

        # Tentativa segura de criar o Áudio
        try:
            # Verifica se ft.Audio existe na versão instalada
            if hasattr(ft, 'Audio'):
                audio_player = ft.Audio(
                    src="https://luan.xyz/files/audio/ambient_c_motion.mp3", 
                    autoplay=False, volume=1.0,
                    on_position_changed=lambda e: atualizar_progresso(e),
                    on_state_changed=lambda e: verificar_fim(e)
                )
                page.overlay.append(audio_player)
            else:
                mostrar_aviso("SEU APP ESTÁ DESATUALIZADO (Sem Áudio)", "red")
        except:
            print("Erro ao iniciar áudio")

        # --- 5. Lógica Principal ---

        def renderizar_playlist():
            lv_playlist.controls.clear()
            if not playlist:
                lv_playlist.controls.append(ft.Text("Playlist vazia.", color="grey", italic=True))
            
            for i, item in enumerate(playlist):
                try:
                    partes = item.split(" - ", 1)
                    titulo_exibicao = partes[1] if len(partes) > 1 else partes[0]
                except: titulo_exibicao = item

                cor_fundo = "blue" if i == current_index and is_playing else "#222222"
                
                # Proteção: alinhamento como string
                conteudo_item = ft.Row([
                    ft.Container(
                        content=ft.Row([
                            ft.Text(f"{i+1}.", size=10, color="grey"),
                            ft.Text(titulo_exibicao, size=12, color="white", no_wrap=True, overflow="ellipsis", expand=True),
                        ]),
                        expand=True,
                        on_click=lambda e, idx=i: tocar_index(idx)
                    ),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="red400", icon_size=18, on_click=lambda e, idx=i: remover_musica(idx))
                ], alignment="spaceBetween") 

                btn_item = ft.Container(content=conteudo_item, padding=ft.padding.only(left=10, right=0, top=2, bottom=2), bgcolor=cor_fundo, border_radius=5)
                lv_playlist.controls.append(btn_item)
            page.update()

        def salvar_tudo():
            try:
                all_playlists[current_playlist_name] = playlist
                page.client_storage.set("all_playlists_data", all_playlists)
                page.client_storage.set("last_playlist_name", current_playlist_name)
            except: pass

        def carregar_tudo():
            nonlocal all_playlists, current_playlist_name, playlist
            try:
                dados_pl = page.client_storage.get("all_playlists_data")
                last_name = page.client_storage.get("last_playlist_name")

                if dados_pl and isinstance(dados_pl, dict):
                    all_playlists = dados_pl
                
                if last_name and last_name in all_playlists:
                    current_playlist_name = last_name
                else:
                    current_playlist_name = list(all_playlists.keys())[0]

                playlist = all_playlists[current_playlist_name]
                lbl_nome_playlist.value = f"Playlist: {current_playlist_name}"
                renderizar_playlist()
            except: pass

        def mudar_para_playlist(nome):
            nonlocal current_playlist_name, playlist, current_index
            if nome not in all_playlists: return
            
            all_playlists[current_playlist_name] = playlist 
            
            current_playlist_name = nome
            playlist = all_playlists[nome]
            current_index = 0
            
            lbl_nome_playlist.value = f"Playlist: {nome}"
            salvar_tudo()
            renderizar_playlist()
            
            if dlg_trocar.open: page.close(dlg_trocar)
            page.update()

        # --- Dialogs ---
        
        txt_nova_pl = ft.TextField(label="Nome da Nova Playlist")
        def criar_nova_playlist(e):
            nome = txt_nova_pl.value.strip()
            if not nome: return
            if nome in all_playlists:
                mostrar_aviso("Nome já existe!", "red")
                return
            
            all_playlists[nome] = []
            mudar_para_playlist(nome)
            dlg_nova.open = False
            txt_nova_pl.value = ""
            page.update()
            mostrar_aviso(f"Playlist '{nome}' criada!")

        dlg_nova = ft.AlertDialog(
            title=ft.Text("Nova Playlist"),
            content=txt_nova_pl,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.close(dlg_nova)),
                ft.TextButton("Criar", on_click=criar_nova_playlist),
            ]
        )

        def abrir_menu_trocar(e):
            lista_opcoes = ft.Column(scroll="auto", height=200)
            for nome in all_playlists.keys():
                cor = "blue" if nome == current_playlist_name else "white"
                # Botão simples para evitar erros de estilo
                btn = ft.TextButton(
                    text=f"{nome} ({len(all_playlists[nome])})", 
                    on_click=lambda e, n=nome: mudar_para_playlist(n)
                )
                lista_opcoes.controls.append(btn)
            
            dlg_trocar.content = lista_opcoes
            page.open(dlg_trocar)

        dlg_trocar = ft.AlertDialog(
            title=ft.Text("Selecionar Playlist"),
            content=ft.Container(),
        )

        def apagar_playlist_atual(e):
            nonlocal current_playlist_name
            if len(all_playlists) <= 1:
                mostrar_aviso("Você não pode apagar a única playlist!", "red")
                page.close(dlg_apagar)
                return
            
            del all_playlists[current_playlist_name]
            nova_pl = list(all_playlists.keys())[0]
            mudar_para_playlist(nova_pl)
            page.close(dlg_apagar)
            mostrar_aviso("Playlist apagada.", "red")

        dlg_apagar = ft.AlertDialog(
            title=ft.Text("Tem certeza?"),
            content=ft.Text("Isso apagará todas as músicas desta playlist."),
            actions=[
                ft.TextButton("Não", on_click=lambda e: page.close(dlg_apagar)),
                ft.TextButton("Sim, Apagar", on_click=apagar_playlist_atual), # Removi style complexo
            ]
        )

        # --- Controles de Reprodução ---

        def remover_musica(index_para_apagar):
            nonlocal playlist, current_index, is_playing
            if index_para_apagar < 0 or index_para_apagar >= len(playlist): return

            if index_para_apagar == current_index:
                if audio_player: audio_player.pause()
                is_playing = False
                lbl_status.value = "Parado"
                btn_play.icon = ft.Icons.PLAY_CIRCLE_FILLED
                img_capa.src = "https://img.icons8.com/fluency/240/music-record.png"
                lbl_titulo.value = "..."
            
            if index_para_apagar < current_index: current_index -= 1

            nome = playlist[index_para_apagar].split(" - ")[-1]
            playlist.pop(index_para_apagar)
            
            salvar_tudo()
            renderizar_playlist()
            mostrar_aviso(f"Removido: {nome}", "red")

        def importar_link(e):
            url = txt_import_url.value
            if not url: return
            lbl_status.value = "Buscando..."
            btn_import.disabled = True
            page.update()

            def tarefa():
                nonlocal playlist
                opts = {'extract_flat': True, 'quiet': True, 'ignoreerrors': True}
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        novas = []
                        if 'entries' in info:
                            for v in info['entries']:
                                if v and v.get('id'): novas.append(f"https://www.youtube.com/watch?v={v['id']} - {v.get('title','Vídeo')}")
                        else:
                            novas.append(f"{info['webpage_url']} - {info.get('title', 'Vídeo')}")
                        
                        playlist.extend(novas)
                        salvar_tudo()
                        renderizar_playlist()
                        mostrar_aviso(f"{len(novas)} músicas em '{current_playlist_name}'", "green")
                        lbl_status.value = "Pronto."
                except Exception as err:
                    mostrar_aviso(f"Erro: {str(err)}", "red")
                
                btn_import.disabled = False
                txt_import_url.value = ""
                page.update()
            threading.Thread(target=tarefa, daemon=True).start()

        def tocar_index(index):
            nonlocal current_index, is_playing
            if not playlist or index < 0 or index >= len(playlist): return
            current_index = index
            renderizar_playlist()
            
            item_completo = playlist[current_index]
            url_original = item_completo.split(" - ")[0].strip()
            titulo = item_completo.split(" - ", 1)[1] if " - " in item_completo else "Vídeo"

            lbl_titulo.value = titulo
            lbl_status.value = "Carregando..."
            if audio_player: audio_player.pause()
            is_playing = False
            btn_play.icon = ft.Icons.PLAY_CIRCLE_FILLED
            page.update()

            def extrair():
                nonlocal is_playing
                if not audio_player:
                    mostrar_aviso("ERRO: Áudio indisponível.", "red")
                    return

                try:
                    ydl_opts = {'format': 'bestaudio[ext=m4a]/bestaudio/best', 'quiet': True, 'noplaylist': True}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url_original, download=False)
                        audio_player.src = info['url']
                        if info.get('thumbnail'): img_capa.src = info['thumbnail']
                        audio_player.update(); time.sleep(0.5); audio_player.play()
                        is_playing = True; lbl_status.value = "Tocando"; btn_play.icon = ft.Icons.PAUSE_CIRCLE_FILLED
                except:
                    mostrar_aviso("Erro ao tocar. Pulando...", "orange")
                    time.sleep(1)
                    proxima(None)
                page.update()
            threading.Thread(target=extrair, daemon=True).start()

        def play_pause(e):
            nonlocal is_playing
            if not audio_player: return
            if is_playing:
                audio_player.pause(); btn_play.icon = ft.Icons.PLAY_CIRCLE_FILLED; is_playing = False
            else:
                if audio_player.src: audio_player.resume(); btn_play.icon = ft.Icons.PAUSE_CIRCLE_FILLED; is_playing = True
                else: tocar_index(current_index)
            page.update()

        def proxima(e):
            if current_index + 1 < len(playlist): tocar_index(current_index + 1)
            else: mostrar_aviso("Fim da playlist", "blue")

        def anterior(e):
            if current_index > 0: tocar_index(current_index - 1)

        def pular_tempo(segundos):
            try: 
                if audio_player:
                    audio_player.seek(int(slider_tempo.value + (segundos * 1000)))
            except: pass

        def toggle_shuffle(e):
            nonlocal is_shuffled
            is_shuffled = not is_shuffled
            if is_shuffled: random.shuffle(playlist); btn_shuffle.icon_color = "green"; mostrar_aviso("Aleatório: ON")
            else: btn_shuffle.icon_color = "white"; mostrar_aviso("Aleatório: OFF")
            renderizar_playlist()
            salvar_tudo()

        # --- Montagem Final da UI ---
        
        btn_import = ft.IconButton(ft.Icons.DOWNLOAD, on_click=importar_link, icon_color="blue")
        btn_prev = ft.IconButton(ft.Icons.SKIP_PREVIOUS, on_click=anterior)
        btn_play = ft.IconButton(ft.Icons.PLAY_CIRCLE_FILLED, icon_size=64, icon_color="blue", on_click=play_pause)
        btn_next = ft.IconButton(ft.Icons.SKIP_NEXT, on_click=proxima)
        btn_shuffle = ft.IconButton(ft.Icons.SHUFFLE, on_click=toggle_shuffle, icon_color="white")
        btn_back_10 = ft.IconButton(ft.Icons.REPLAY_10, on_click=lambda e: pular_tempo(-10), icon_size=20)
        btn_fwd_10 = ft.IconButton(ft.Icons.FORWARD_10, on_click=lambda e: pular_tempo(10), icon_size=20)

        # CORREÇÃO PRINCIPAL: Menu Popup Compatível com Versões Antigas
        # Usamos 'content' em vez de 'text' e 'icon'
        btn_menu = ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT,
            tooltip="Opções",
            items=[
                ft.PopupMenuItem(
                    content=ft.Row([ft.Icon(ft.Icons.LIBRARY_MUSIC), ft.Text("Trocar Playlist")]),
                    on_click=abrir_menu_trocar
                ),
                ft.PopupMenuItem(
                    content=ft.Row([ft.Icon(ft.Icons.ADD_BOX), ft.Text("Nova Playlist")]),
                    on_click=lambda e: page.open(dlg_nova)
                ),
                ft.PopupMenuItem(
                    content=ft.Row([ft.Icon(ft.Icons.DELETE_FOREVER), ft.Text("Apagar Playlist")]),
                    on_click=lambda e: page.open(dlg_apagar)
                ),
            ]
        )

        page.add(
            ft.Column([
                ft.Row([lbl_Andre], alignment="center"),
                ft.Row([txt_import_url, btn_import], alignment="center"),
                ft.Row([lbl_nome_playlist], alignment="center"),
                ft.Divider(height=1, color="grey"),
                ft.Column([
                    ft.Row([img_capa], alignment="center"),
                    lbl_titulo,
                    lbl_status,
                    ft.Container(height=10),
                    ft.Row([lbl_tempo_now, slider_tempo, lbl_tempo_total], alignment="spaceBetween"),
                    ft.Row([
                        btn_shuffle, btn_back_10, btn_prev, btn_play, btn_next, btn_fwd_10, btn_menu
                    ], alignment="center", spacing=0),
                ], spacing=0),
                ft.Divider(height=1, color="grey"),
                ft.Container(content=lv_playlist, expand=True, bgcolor="#111111", border_radius=10),
            ], expand=True)
        )

        carregar_tudo()

        # --- FIM DO SEU CÓDIGO ---

    except Exception as e:
        page.clean()
        page.bgcolor = "black"
        page.add(
            ft.Column([
                ft.Text("ERRO FATAL (Ainda!)", size=20, weight="bold", color="red"),
                ft.Text(f"Erro: {str(e)}", size=16, color="white"),
                ft.Divider(color="white"),
                ft.Text(traceback.format_exc(), size=10, color="yellow", font_family="monospace")
            ], scroll="auto", expand=True)
        )
        page.update()

ft.app(target=main)
