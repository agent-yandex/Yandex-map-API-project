from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import requests
import os
import math
import itertools
import sys


API_KEY = '40d1649f-0493-4b70-98ba-98533de7710b'
LAT_STEP = 0.002  # Шаги при движении карты по широте и долготе
LON_STEP = 0.002


class Window(QWidget):
    def __init__(self):
        super().__init__(windowTitle='API map')
        self.setFixedSize(600, 450)
        self.lat = 59.123794  # Координаты центра карты на старте
        self.lon = 37.986265
        self.zoom = 15  # Масштаб карты на старте
        self.type = "map"
        self.search_result = False
        # Блокировка/активация поля воода адреса
        self.search_prot = itertools.cycle([True, False])
        self.do_paint = True
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout(self)
        self.address = QLineEdit(self)
        self.address.setEnabled(False)
        layout.addWidget(self.address, alignment=Qt.AlignTop)
        layout.addWidget(QPushButton('Поиск', clicked=self.search,
                                     enabled=False), alignment=Qt.AlignTop)

    def search(self):
        self.search_result = True
        self.do_paint = True
        self.repaint()
        # toponym_to_find = self.address.text()
        # if toponym_to_find:
        #     lat, lon = get_coordinates(toponym_to_find)
        #     ll_spn = f'll={lat},{lon}&spn=0.005,0.005'
        #     map_request = f'http://static-maps.yandex.ru/1.x/?{ll_spn}&l={self.type}' \
        #                   f'&pt={lat},{lon}'

        #     response = requests.get(map_request)

        #     if not response:
        #         print("Ошибка выполнения запроса:")
        #         print(map_request)
        #         print("Http статус:", response.status_code, "(", response.reason, ")")
        #         sys.exit(1)

        #     self.search_result = True
        #     map_file = "map.png"
        #     try:
        #         with open(map_file, "wb") as file:
        #             file.write(response.content)
        #     except IOError as ex:
        #         print("Ошибка записи временного файла:", ex)
        #         sys.exit(2)

    def ll(self):
        return f'{self.lon},{self.lat}'

    def paintEvent(self, event):
        if self.do_paint:
            self.do_paint = False
            qp = QPainter(self)
            qp.drawImage(0, 0, QImage(self.load_map()))

    def load_map(self):
        if self.search_result:
            self.search_result = False
            toponym_to_find = self.address.text()
            if toponym_to_find:
                self.lon, self.lat = get_coordinates(toponym_to_find)
                self.zoom = 18
                ll_spn = f'll={self.lon},{self.lat}&z={self.zoom}'
                map_request = f'http://static-maps.yandex.ru/1.x/?{ll_spn}&l={self.type}' \
                              f'&pt={self.lon},{self.lat},comma'
                response = requests.get(map_request)

        else:
            map_request = "http://static-maps.yandex.ru/1.x/?ll={ll}&z={z}&l={type}".format(ll=self.ll(),
                                                                                            z=self.zoom,
                                                                                            type=self.type)

        response = requests.get(map_request)
        if not response:
            print('Ошибка выполнения запроса')
            print(map_request)
            print(f'Http статус: {response.status_code} ({response.reason})')
            sys.exit(1)

        self.map_file = 'map.png'
        try:
            with open(self.map_file, 'wb') as file:
                file.write(response.content)
        except IOError as ex:
            print("Ошибка записи временного файла:", ex)
            sys.exit(2)

        return self.map_file

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_PageUp and self.zoom < 20:
            self.zoom += 1
        elif event.key() == Qt.Key_PageDown and self.zoom > 2:
            self.zoom -= 1
        elif event.key() == Qt.Key_Up and self.lat < 85 - LAT_STEP * math.pow(2, 15 - self.zoom):
            self.lat += LAT_STEP * math.pow(2, 15 - self.zoom)
        elif event.key() == Qt.Key_Down and self.lat > -85 + LAT_STEP * math.pow(2, 15 - self.zoom):
            self.lat -= LAT_STEP * math.pow(2, 15 - self.zoom)
        elif event.key() == Qt.Key_Left:
            self.lon -= LON_STEP * math.pow(2, 15 - self.zoom)
        elif event.key() == Qt.Key_Right:
            self.lon += LON_STEP * math.pow(2, 15 - self.zoom)
        elif event.key() == Qt.Key_Alt:
            # Активация/блокировка поля ввода адреса
            solution = next(self.search_prot)
            self.address.setEnabled(solution)
            self.findChild(QPushButton).setEnabled(solution)
        elif event.key() == Qt.Key_1:
            self.type = 'map'
        elif event.key() == Qt.Key_2:
            self.type = 'sat'
        elif event.key() == Qt.Key_3:
            self.type = 'sat,skl'
        self.do_paint = True
        self.repaint()


def geocode(address):
    # Собираем запрос для геокодера.
    geocoder_request = f"http://geocode-maps.yandex.ru/1.x/?apikey={API_KEY}" \
        f"&geocode={address}&format=json"

    # Выполняем запрос.
    response = requests.get(geocoder_request)

    if response:
        # Преобразуем ответ в json-объект
        json_response = response.json()
    else:
        raise RuntimeError(
            """Ошибка выполнения запроса:
            {request}
            Http статус: {status} ({reason})""".format(
                request=geocoder_request, status=response.status_code, reason=response.reason))

    # Получаем первый топоним из ответа геокодера.
    # Согласно описанию ответа он находится по следующему пути:
    features = json_response["response"]["GeoObjectCollection"]["featureMember"]
    return features[0]["GeoObject"] if features else None


# Получаем координаты объекта по его адресу.
def get_coordinates(address):
    toponym = geocode(address)
    if not toponym:
        return None, None

    # Координаты центра топонима:
    toponym_coodrinates = toponym["Point"]["pos"]
    # Широта, преобразованная в плавающее число:
    toponym_longitude, toponym_lattitude = toponym_coodrinates.split(" ")
    return float(toponym_longitude), float(toponym_lattitude)


app = QApplication([])
window = Window()
window.show()
app.exec()
os.remove(window.map_file)
