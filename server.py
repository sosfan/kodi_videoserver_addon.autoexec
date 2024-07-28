import threading
import socket
import xbmc
import xbmcgui
import xbmcaddon

# Variable global para controlar el estado del servidor
server_running = True

# Función para reproducir una URL recibida usando xbmc.executebuiltin
def reproducir_url(url, client_socket):
    try:
        xbmc.executebuiltin(f'PlayMedia({url}, noresume)')
        # Esperar hasta que comience la reproducción
        contador = 100
        while not xbmc.getCondVisibility('Player.Playing'):
            xbmc.sleep(50)
            contador -= 1
            if contador <= 0:
                xbmc.log("Error: No se pudo iniciar la reproducción.", level=xbmc.LOGERROR)
                break
        if xbmc.getCondVisibility('Player.Playing'):
            # Una vez que la reproducción haya comenzado, pausar el video
            while not xbmc.getCondVisibility('Player.Paused'):
                xbmc.Player().pause()
                xbmc.sleep(50)
            client_socket.sendall(b"<STREAMOK>\n")
            xbmc.log("Reproducción pausada exitosamente.", level=xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"Error: {str(e)}", level=xbmc.LOGERROR)

def handle_commands(client_socket):
    activate_screensaver = xbmcaddon.Addon().getSettingBool('activate_screensaver')
    if activate_screensaver:
        xbmc.executebuiltin(f'ActivateScreensaver')
    mute_while_playing = xbmcaddon.Addon().getSettingBool('mute_while_playing')
    if mute_while_playing:
        if not xbmc.getCondVisibility('Player.Muted'):
            xbmc.executebuiltin('Mute')
    try:
        while True:
            data = client_socket.recv(1024).decode().strip()
            if not data:
                xbmcgui.Dialog().notification('SKmJukebox', 'Cliente desconectado', xbmcaddon.Addon().getAddonInfo('icon'), 5000)
                xbmc.Player().stop()
                if xbmc.getCondVisibility('Player.Muted'):
                    xbmc.executebuiltin('Mute')
                break
            if data == "<PAUSE>":
                if xbmc.Player().isPlaying() and xbmc.getCondVisibility('Player.Paused'):
                    mute_while_playing = xbmcaddon.Addon().getSettingBool('mute_while_playing')
                    if mute_while_playing:
                        if not xbmc.getCondVisibility('Player.Muted'):
                            xbmc.executebuiltin('Mute')
                    xbmc.Player().pause()
                    client_socket.sendall(b"<OK>\n")
            elif data == "<ENDFILE>":
                xbmc.Player().stop()
                activate_screensaver = xbmcaddon.Addon().getSettingBool('activate_screensaver')
                if activate_screensaver:
                    xbmc.executebuiltin(f'ActivateScreensaver')
                client_socket.sendall(b"<OK>\n")
            elif data == "<RESTART>":
                client_socket.sendall(b"<OK>\n")
            elif data == "<CANCEL>":
                xbmc.Player().stop()
                client_socket.sendall(b"<OK>\n")
            elif data == "<DELETEFILE>":
                client_socket.sendall(b"<OK>\n")
            elif data == "<ISCONNECTED>":
                client_socket.sendall(b"<OK>\n")
            elif "http://" in data:
                client_socket.sendall(b"<OK>\n")
                reproducir_url(data, client_socket)
    except (socket.error, ConnectionResetError):
        xbmc.log("Se ha detectado la desconexión del cliente.", level=xbmc.LOGINFO)
    finally:
        client_socket.close()
        xbmc.log("Socket del cliente cerrado.", level=xbmc.LOGINFO)

def main():
    global server_running
    host = ''
    port_commands = 5010
    server_socket_commands = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket_commands.bind((host, port_commands))
    server_socket_commands.listen(5)
    xbmc.log("Servidor socket escuchando el puerto para comandos: {}".format(port_commands), level=xbmc.LOGINFO)

    try:
        while server_running:
            server_socket_commands.settimeout(1.0)
            try:
                client_socket_commands, client_address_commands = server_socket_commands.accept()
                xbmc.log("Cliente conectado para comandos: {}".format(client_address_commands), level=xbmc.LOGINFO)
                xbmcgui.Dialog().notification('SKmJukebox', 'Nueva conexión aceptada', xbmcaddon.Addon().getAddonInfo('icon'), 5000)
                client_socket_commands.sendall(b"<kodiaddon>\n")
                handle_commands(client_socket_commands)
            except socket.timeout:
                continue
    finally:
        server_socket_commands.close()
        xbmc.log("Servidor socket cerrado.", level=xbmc.LOGINFO)

if __name__ == "__main__":
    server_thread = threading.Thread(target=main)
    server_thread.start()
    
    addon = xbmcaddon.Addon()
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            server_running = False
            server_thread.join()
            break
