# ASK-Vision

Система видеонаблюдения с модулем автоматической детекции движения.

## Возможности

- Многокамерный просмотр (Live View)
- Детекция движения (Background Subtraction)
- Два режима записи: по движению и постоянная запись
- Внутренний плеер записей
- Журнал событий + экспорт в CSV
- Очистка журнала
- Гибкая сетка камер

## Технологии

- Python 3.12
- PyQt5
- OpenCV
- SQLite

## Установка и запуск

```bash
git clone https://github.com/yarivol/ASK-Vision.git
cd ASK-Vision
python -m venv venv
venv\Scripts\activate          # only Windows
pip install -r requirements.txt
python main.py
