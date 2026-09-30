# Развёртывание ASK-Vision на Debian 12

Инструкция рассчитана на виртуальную машину с Debian 12 и графическим интерфейсом.

## 1. Подготовить систему

Если Debian 12 установлен без GUI, сначала поставьте рабочий стол, например `XFCE` или `GNOME`.  
Для приложения нужен графический сеанс.

Обновите систему:

```bash
sudo apt update
sudo apt upgrade -y
```

Поставьте нужные пакеты:

```bash
sudo apt install -y \
  git \
  python3 \
  python3-venv \
  python3-pip \
  libgl1 \
  libglib2.0-0 \
  libxkbcommon-x11-0 \
  libxcb-xinerama0 \
  libxcb-cursor0 \
  ffmpeg
```

Если нужен локальный USB-захват камеры:

```bash
sudo apt install -y v4l-utils
```

## 2. Скопировать проект

Вариант 1. Через `git`:

```bash
git clone <URL_ВАШЕГО_РЕПОЗИТОРИЯ>
cd ASK-Vision
```

Вариант 2. Если проект уже у вас на Windows:

- выключите виртуалку
- подключите Shared Folder в VirtualBox/VMware
- либо передайте архив проекта по `scp`/`sftp`

Важно: папку `venv` из Windows в Linux не переносить.  
Linux должен создать своё окружение заново.

## 3. Создать виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Первый запуск

```bash
python3 main.py
```

Если всё нормально, откроется окно входа ASK-Vision.

Стандартные учётные записи:

- `admin / password`
- `operator / operator`

> ⚠️ При первом входе приложение **принудительно потребует сменить стандартный пароль**
> (минимум 8 символов). До смены пароля автологин для такой учётной записи не сработает.

Если хочешь запускать одной командой:

```bash
chmod +x run.sh
./run.sh
```

## 5. Если не открывается окно

Проверьте, что вы вошли именно в графический сеанс Debian, а не просто в консоль `tty`.

Проверьте переменную дисплея:

```bash
echo $DISPLAY
```

Если она пустая, приложение не сможет показать GUI.

## 6. Автозапуск в Linux

В приложении уже сделана поддержка Linux-автозапуска.  
Когда в настройках включается автозапуск, создаётся файл:

```bash
~/.config/autostart/ask-vision.desktop
```

Он будет запускать `main.py` при входе пользователя в графическую сессию.

## 7. Проверка локальной камеры

Для Debian локальная камера открывается через Linux backend `V4L2`.

Проверить, видит ли система устройства камеры:

```bash
v4l2-ctl --list-devices
```

Если камер нет в списке, проблема не в ASK-Vision, а в доступе виртуалки к USB-устройству.

## 8. Если камера проброшена в виртуалку

Для VirtualBox:

1. Выключите VM.
2. Откройте `Settings -> USB`.
3. Включите `USB Controller`.
4. Добавьте вашу USB-камеру в фильтр устройств.
5. Запустите VM снова.

После этого проверьте:

```bash
ls /dev/video*
```

Если появилось что-то вроде `/dev/video0`, камера проброшена.

## 9. Если нужен запуск после перезагрузки

Запустите приложение один раз вручную, войдите под `admin`, затем:

1. Откройте `Настройки программы`
2. Включите `Автозапуск при старте системы`
3. При необходимости включите `Автологин`
4. Сохраните настройки

## 10. Полезная схема работы на VM

- храните проект в домашней папке пользователя, например `/home/user/ASK-Vision`
- архив `videos/` лучше держать на диске с достаточным объёмом
- если запись идёт с IP-камер, проверьте доступность сети из виртуалки
- если запись идёт на USB-диск, сначала смонтируйте его в Debian

## 11. Частые проблемы

`Could not load the Qt platform plugin "xcb"`:

```bash
sudo apt install -y libxkbcommon-x11-0 libxcb-xinerama0 libxcb-cursor0
```

Если ошибка показывает путь вида `cv2/qt/plugins`, значит у тебя конфликт `opencv-python` и `PyQt5`.
Исправляется так:

```bash
deactivate 2>/dev/null || true
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
unset QT_QPA_PLATFORM_PLUGIN_PATH
unset QT_PLUGIN_PATH
unset QT_QPA_FONTDIR
export QT_QPA_PLATFORM=xcb
python3 main.py
```

После обновления проекта можно просто использовать:

```bash
./run.sh
```

`cv2` не открывает окно или поток:

- проверьте, что камера доступна в Debian
- проверьте RTSP/HTTP URL
- проверьте, что виртуалка имеет доступ в сеть

Открывается приложение, но нет картинки с USB-камеры:

- проверьте `ls /dev/video*`
- проверьте `v4l2-ctl --list-devices`
- проверьте USB passthrough в VirtualBox/VMware
