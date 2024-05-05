import os
import platform
import time
import tkinter as tk
from PyQt5 import QtGui
from appdirs import *
import urllib.request
from urllib.parse import urlparse
import json
import hashlib
from osarch import detect_system_architecture
from pyunpack import Archive
import subprocess
from tkinter.font import BOLD, Font

OS_NAME, OS_ARCH = detect_system_architecture() # Linux: Linux | Mac: Darwin | Windows: Windows
VERSION:str = "2.0.0" # TODO Changer la version
isException:bool = False

def resource_path(relative_path:str):
    try:
        base_path = os.sys._MEIPASS
    except Exception:
        base_path = os.path.abspath("./resources/") # ".": pour le build | "./resources/": pour le run

    return os.path.join(base_path, relative_path)

def loadProperties(path:str):
    result={}
    with open(path, "r") as file:
        file.readline()
        while True:
            txt = file.readline()
            if txt == "":
                break
            split = str(txt).split("=")
            result[split[0]]=split[1].rstrip()
        file.close()
    return result

root:tk.Tk = tk.Tk("Astrauworld launcher")
root.attributes('-alpha', 0.0) #For icon
root.iconbitmap(default=resource_path("logo.ico"))
#root.lower()
root.iconify()
win = tk.Toplevel(root)
win.geometry("346x446")
win.overrideredirect(True)

astrauworldDir:str = user_data_dir("Astrauworld Launcher", False, roaming=True)

customJavaDir:str = os.path.join(astrauworldDir, "java")
currentPropertiesDir:str = os.path.join(astrauworldDir, "launcher.properties")
oldCurrentPropertiesDir:str = os.path.join(astrauworldDir, "currentLauncher.properties")
newPropertiesDir:str = os.path.join(astrauworldDir, "newLauncher.properties")
launcherJar:str = os.path.join(astrauworldDir, "launcher.jar")
libsDir:str = os.path.join(astrauworldDir, "libs")

libsJsonURL:str = "https://raw.githubusercontent.com/AstrauworldMC/launcher/main/src/main/resources/libs.json"
libsPlatformJsonURL:str = "https://raw.githubusercontent.com/AstrauworldMC/launcher/main/src/main/resources/libs"

currentSaver:dict = {}
newSaver:dict = {}

photo = tk.PhotoImage(file = resource_path("splash.png"))
w = tk.Label(win, image=photo)
infosLabel:tk.Label = tk.Label(win, text="Lancer", justify="center", foreground="white", background="#1e1e1e", font=Font(win, size=20, weight=BOLD))

def println(string:str):
    now = time.localtime()

    print("["+ str(now[3]) + ":" + str(now[4]) + ":" + str(now[5]) +"] [Astrauworld Updater] " + string)

def sha1(url):
    with urllib.request.urlopen(url) as response:
        if False and url != response.geturl():
            print("# {} -> {}\n".format(url, response.geturl()))
        sha1 = hashlib.new("SHA1")
        if response.status == 200:
            size, n = 0, 16484
            buf = bytearray(n)
            while n != 0:
                n = response.readinto(buf)
                size += n
                if n > 0:
                    sha1.update(buf[:n])
            o = urlparse(url)
            if not os.path.basename(o.path):
                o = urlparse(response.geturl())
            filename = os.path.basename(o.path) or "index.html"
            return sha1.hexdigest().lower()
        else:
            println(
                "ERROR: %s returned %d (%s)" % (url, response.status, response.reason),
                file=sys.stderr,
            )


def getJarLink():
    return "https://github.com/AstrauworldMC/launcher/releases/download/" + newSaver["launcherVersion"] + "/launcher.jar"

def setPropertiesFiles():
    global newSaver

    with open(newPropertiesDir, "w") as newPropertiesTemp:
        newPropertiesTemp.close()

    try:
        urllib.request.urlretrieve('https://raw.githubusercontent.com/AstrauworldMC/launcher/main/src/main/resources/launcher.properties', newPropertiesDir)
        newSaver = loadProperties(newPropertiesDir)
    except:
        try:
            os.remove(currentPropertiesDir)
        except OSError:
            pass
        try:
            os.remove(newPropertiesDir)
        except OSError:
            pass
        try:
            os.remove(launcherJar)
        except OSError:
            pass
        raise Exception("Problème lors de la vérification de la version")

    if currentSaver["launcherVersion"]==None:
        with open(currentPropertiesDir, "w") as currentPropertiesTemp:
            currentPropertiesTemp.close()

def verifyBootstrapVersion():
    if VERSION != newSaver["bootstrapVersion"]:
        raise Exception("Nouvelle version de l'updater disponible")

def updateJar():
    println("")
    println("---- JAR UPDATE ----")

    println("Current: " + currentSaver["launcherVersion"])
    println("New: " + newSaver["launcherVersion"])
    if currentSaver["launcherVersion"]!=newSaver["launcherVersion"]:
        println("pas égal")
        try:
            urllib.request.urlretrieve(getJarLink(), launcherJar)
        except:
            try:
                os.remove(currentPropertiesDir)
            except OSError:
                pass
            try:
                os.remove(newPropertiesDir)
            except OSError:
                pass
            try:
                os.remove(launcherJar)
            except OSError:
                pass
            raise Exception("Problème lors du téléchargement de la mise à jour du launcher")
        println("jar downloaded")
        with open(newPropertiesDir, "w") as newProps:
            currentProps = open(currentPropertiesDir, "r")
            newProps.write(currentProps.read())
    else:
        println("Dernière version détectée")

def updateLibs():
    global libsJsonURL, libsPlatformJsonURL
    libsExtFiles:list = json.load(urllib.request.urlopen(libsJsonURL))["extfiles"]
    libsPlatformExtFiles:list = json.load(urllib.request.urlopen(libsPlatformJsonURL))["extfiles"]

    libsExtFiles+=libsPlatformExtFiles

    try:
        os.makedirs(libsDir)
    except OSError:
        pass

    for lib in libsExtFiles:
        if os.path.isfile(os.path.join(libsDir, lib["path"])):
            if lib["sha1"]!=hashlib.sha1(open(os.path.join(libsDir, lib["path"]), "rb").read()).hexdigest(): # TODO SHA1
                urllib.request.urlretrieve(lib["downloadURL"], os.path.join(libsDir, lib["path"]))
        else:
            with open(os.path.join(libsDir, lib["path"]), "w") as temp:
                temp.close
            println("Téléchargement de " + lib["path"])
            urllib.request.urlretrieve(lib["downloadURL"], os.path.join(libsDir, lib["path"]))

def update():
    global currentSaver, newSaver, customJavaDir

    try:
        os.mkdir(astrauworldDir)
    except OSError:
        pass

    if not isException:
        setPropertiesFiles()

        currentSaver = loadProperties(currentPropertiesDir)
        newSaver = loadProperties(newPropertiesDir)

    if not isException:
        verifyBootstrapVersion()

    if not isException:
        customJavaDir = getJava()

    if not isException:
        updateLibs()

    if not isException:
        updateJar()

def getJava():
    println("")
    println("---- JAVA 17 VERIF ----")

    try:
        println("-- Vérification du %JAVA_HOME% --")
        javaHome = os.getenv("JAVA_HOME")
        javaHomeSplit1 = javaHome.split(";")
        javaHomeSplit2 = javaHomeSplit1[0].split(os.sep)
        firstReferencedJavaVersion = javaHomeSplit2[len(javaHomeSplit2)-1]
        javaHomeSplit3 = firstReferencedJavaVersion.split(".")
        firstReferencedJavaGlobalVersion = javaHomeSplit3[0]
        println("%JAVA_HOME%: " + javaHome);
        println("First referenced java: " + javaHomeSplit1[0]);
        println("Last part of first referenced java: " + firstReferencedJavaVersion);
        println("First referenced java global version: " + firstReferencedJavaGlobalVersion);

        if "17" in firstReferencedJavaGlobalVersion:
            return javaHomeSplit1[0]
        else:
            raise Exception("Java 17 non trouvé dans %JAVA_HOME%")

    except:
        jre17 = os.path.join(customJavaDir, "jre-17")

        println(r"Aucun Java 17 dans %JAVA_HOME% détecté")

        try:
            os.makedirs(customJavaDir)
        except OSError:
            pass

        if "windows" in OS_NAME.lower():
            if os.path.exists(os.path.join(jre17, "bin", "java.exe")):
                return jre17
            else:
                if OS_ARCH=="64":
                    zip = os.path.join(customJavaDir, "jre17.zip")
                    println("Téléchargement de Java 17 pour Windows 64bits")
                    urllib.request.urlretrieve("https://download.bell-sw.com/java/17.0.6+10/bellsoft-jre17.0.6+10-windows-amd64-full.zip", zip)
                    Archive(zip).extractall(customJavaDir)
                    os.remove(zip)
                    os.replace(os.path.join(customJavaDir, "jre-17.0.6-full"), jre17)
                    return jre17
                elif OS_ARCH=="32":
                    zip = os.path.join(customJavaDir, "jre17.zip")
                    println("Téléchargement de Java 17 pour Windows 32bits")
                    urllib.request.urlretrieve("https://download.bell-sw.com/java/17.0.6+10/bellsoft-jre17.0.6+10-windows-i586-full.zip", zip)
                    Archive(zip).extractall(customJavaDir)
                    os.remove(zip)
                    os.replace(os.path.join(customJavaDir, "jre-17.0.6-full"), jre17)
                    return jre17
                else:
                    raise RuntimeError("Erreur au téléchargement de Java 17")

        elif "darwin" in OS_NAME.lower():
            if os.path.exists(os.path.join(jre17, "bin", "java")):
                return jre17
            else:
                zip = os.path.join(customJavaDir, "jre17.zip")
                println("Téléchargement de Java 17 pour Mac")
                urllib.request.urlretrieve("https://download.bell-sw.com/java/17.0.6+10/bellsoft-jre17.0.6+10-macos-amd64-full.zip", zip)
                Archive(zip).extractall(customJavaDir)
                os.remove(zip)
                os.replace(os.path.join(customJavaDir, "jre-17.0.6-full.jre"), jre17)
                return jre17

        elif "linux" in OS_NAME.lower():
            if os.path.exists(os.path.join(jre17, "bin", "java")):
                return jre17
            else:
                if OS_ARCH=="64":
                    zip = os.path.join(customJavaDir, "jre17.tar.gz")
                    println("Téléchargement de Java 17 pour Linux 64bits")
                    urllib.request.urlretrieve("https://download.bell-sw.com/java/17.0.6+10/bellsoft-jre17.0.6+10-linux-amd64-full.tar.gz", zip)
                    Archive(zip).extractall(customJavaDir)
                    os.remove(zip)
                    os.replace(os.path.join(customJavaDir, "jre-17.0.6-full"), jre17)
                    return jre17
                elif OS_ARCH=="32":
                    zip = os.path.join(customJavaDir, "jre17.tar.gz")
                    println("Téléchargement de Java 17 pour Linux 32bits")
                    urllib.request.urlretrieve("https://download.bell-sw.com/java/17.0.6+10/bellsoft-jre17.0.6+10-linux-i586.tar.gz", zip)
                    Archive(zip).extractall(customJavaDir)
                    os.remove(zip)
                    os.replace(os.path.join(customJavaDir, "jre-17.0.6-full"), jre17)
                    return jre17
                else:
                    raise RuntimeError("Erreur au téléchargement de Java 17")

        else:
            println("OS non supporté");
            return None

def launch():

    println("")
    println("---- LAUNCH ----")

    try:
        os.remove(newPropertiesDir)
    except OSError:
        pass

    javaCommand:str
    java = os.path.join(customJavaDir, "bin", "java")
    if "windows" in OS_NAME.lower():
        javaCommand = "\"" + java + "\""
    else:
        javaCommand = java

    javaCommand += " -cp "

    if "windows" in OS_NAME.lower():
        javaCommand += "\""
    javaCommand += launcherJar

    if "windows" in OS_NAME.lower():
        javaCommand += ";"
    else:
        javaCommand += ":"

    javaCommand += os.path.join(libsDir,"*")
    if "windows" in OS_NAME.lower():
        javaCommand += "\" "

    javaCommand += "fr.timeto.astrauworld.launcher.main.Main"
    print(javaCommand)

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    sub = subprocess.Popen(javaCommand, startupinfo=startupinfo)
    if "darwin" not in OS_NAME.lower():
        root.destroy()
        sub.wait()
    exit(0)

def main(e):
    global isException, libsPlatformJsonURL, currentSaver
    try:
        isException = False

        if "windows" in OS_NAME.lower():
            println("Windows OK")
            libsPlatformJsonURL += "-win.json"
        elif "darwin" in OS_NAME.lower():
            println("Mac OK")
            libsPlatformJsonURL += "-mac.json"
        elif "linux" in OS_NAME.lower():
            println("Linux OK")
            libsPlatformJsonURL += "-linux.json"
        else:
            println("OS non supporté")

        println("Astrauworld Launcher dir: " + astrauworldDir)

        try:
            currentSaver=loadProperties(currentPropertiesDir)
        except OSError:
            with open(currentPropertiesDir, "w") as temp:
                temp.write("#Astrauworld Launcher properties\n")
                temp.write("launcherVersion= \n")
                temp.write("bootstrapVersion="+VERSION+"\n")
                temp.close()
            currentSaver=loadProperties(currentPropertiesDir)

        try:
            os.remove(oldCurrentPropertiesDir)
        except OSError:
            pass

        if not isException:
            update()

        if not isException:
            launch()

    except TypeError as e:
        isException=True
        println(str(e))
        exit(1)

win.update_idletasks()
app = QtGui.QGuiApplication([])
screen_width = app.screens()[0].geometry().width()
screen_height = app.screens()[0].geometry().height()

size = tuple(int(_) for _ in win.geometry().split('+')[0].split('x'))
x = screen_width/2 - size[0]/2
y = screen_height/2 - size[1]/2

win.geometry("+%d+%d" % (x, y))

w.pack()

hovered = False
def changeColor(e):
    global hovered
    text=["Lancement...","Lancer"]
    color=["red","white"]
    infosLabel.config(text=text[int(hovered)], foreground=color[int(hovered)])
    hovered = not hovered

infosLabel.place(x=34, y=355, width=278, height=50)
infosLabel.bind("<Button-1>", main)
infosLabel.bind("<Enter>", changeColor)
infosLabel.bind("<Leave>", changeColor)

win.mainloop()
