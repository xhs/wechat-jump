#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PIL import Image, ImageDraw

import os
import time
import math

TOP_SECRET = 2.326
DEBUG = True


def take_and_download_screenshot():
    os.system('adb shell screencap -p /sdcard/wechat-jump.png')
    file_path = f'screenshots/{int(time.time())}.png'
    os.system(f'adb pull /sdcard/wechat-jump.png {file_path}')
    return file_path


def get_cropped_image(path):
    original = Image.open(path)
    width, height = original.size
    return original.crop((0, height * 0.2, width, height * 0.9))


def get_grayscale_image(image):
    grayscale = image.convert('L')
    width, height = grayscale.size

    high_sum = low_sum = 0
    for w in range(width):
        high_sum += grayscale.getpixel((w, 0))
        low_sum += grayscale.getpixel((w, height - 1))
    high = math.ceil(high_sum / width)
    low = math.floor(low_sum / width)
    background_colors = set()
    for h in range(height):
        color = grayscale.getpixel((width - 1, h))
        if low <= color <= high:
            background_colors.add(color)

    for w in range(width):
        for h in range(height):
            if grayscale.getpixel((w, h)) in background_colors:
                grayscale.putpixel((w, h), high)

    return grayscale


class Point(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return f'({self.x}, {self.y})'

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    @staticmethod
    def of(p):
        return Point(p.x, p.y)


class PointFound(Exception):
    def __init__(self, x, y):
        super().__init__()
        self.x = x
        self.y = y


def get_destination_top_from_top_left(image):
    background_color = image.getpixel((0, 0))
    width, height = image.size
    top_left = None
    try:
        for h in range(height):
            for w in range(width):
                if image.getpixel((w, h)) != background_color:
                    raise PointFound(w, h)
    except PointFound as p:
        top_left = Point(p.x, p.y)

    top_right = Point.of(top_left)
    while image.getpixel((top_right.x + 1, top_right.y)) != background_color:
        top_right.x += 1

    return Point((top_left.x + top_right.x) // 2, top_left.y)


def get_destination_top_from_left_top(image):
    background_color = image.getpixel((0, 0))
    width, height = image.size
    y = height - 1
    top_left = None
    try:
        for w in range(width):
            for h in range(height):
                if image.getpixel((w, h)) != background_color:
                    if h > y:
                        raise PointFound(w, y)
                    y = h
                    break
    except PointFound as p:
        top_left = Point(p.x, p.y)

    top_right = Point.of(top_left)
    while image.getpixel((top_right.x + 1, top_right.y)) != background_color:
        top_right.x += 1

    return Point((top_left.x + top_right.x) // 2, top_left.y)


def get_destination_top(image):
    top1 = get_destination_top_from_left_top(image)
    top2 = get_destination_top_from_top_left(image)
    if top1 != top2 and top1.y > top2.y:
        return top2
    return top1


def get_destination_right(image, top):
    background_color = image.getpixel((0, 0))
    tracking = Point(top.x, top.y)
    count = 0
    while True:
        if image.getpixel((tracking.x + 1, tracking.y)) != background_color:
            tracking.x += 1
            count = 0
        elif image.getpixel((tracking.x, tracking.y + 1)) != background_color and count < 3:
            tracking.y += 1
            count += 1
        else:
            return Point(tracking.x, tracking.y)


def locate_destination(image):
    top = get_destination_top(image)
    right = get_destination_right(image, top)
    return Point(top.x, right.y)


def locate_source(image):
    width, height = image.size
    for w in range(width):
        for h in range(height):
            pixel = image.getpixel((w, h))
            if pixel[0] == 43 and pixel[1] == 43 and pixel[2] == 73:
                return Point(w + 25, h + 5)


def jump_dude_jump(distance):
    t = int(distance * TOP_SECRET)
    os.system(f'adb shell input swipe 10 10 10 11 {t}')
    time.sleep(t / 1000)


if __name__ == '__main__':
    if DEBUG:
        os.makedirs('screenshots', exist_ok=True)
        os.makedirs('traces', exist_ok=True)

    while True:
        path = take_and_download_screenshot()

        cropped = get_cropped_image(path)
        grayscale = get_grayscale_image(cropped)

        dest = locate_destination(grayscale)
        src = locate_source(cropped)
        distance = math.sqrt((dest.x - src.x) ** 2 + (dest.y - src.y) ** 2)
        print(src, dest, distance)

        if DEBUG:
            draw = ImageDraw.Draw(grayscale)
            draw.line([(src.x, src.y), (dest.x, dest.y)], fill='black')
            grayscale.save(f'traces/{int(time.time())}.png')

        jump_dude_jump(distance)
        time.sleep(0.8)
