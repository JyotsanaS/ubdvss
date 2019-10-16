#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (С) ABBYY (BIT Software), 1993 - 2018. All rights reserved.
"""
Всевозможные вспомогательные функции
"""
import logging
import os

import cv2
import numpy as np
from PIL import Image
from shapely.geometry import Polygon, MultiPoint


def fix_quadrangle(quad):
    """
    :param quad: список 4x точек на плоскости
    :return: четырехугольник являющийся выпуклой оболочкой
    """
    word_poly = Polygon(quad)
    is_valid = word_poly.is_valid
    if not is_valid:
        logging.info('polygon invalid')
        fixed_word_poly = MultiPoint(quad).convex_hull
        fixed_quad = np.array(fixed_word_poly.exterior.coords[:4])
        return fixed_quad
    return np.array(quad)


def pillow_rgb_fromarray(img):
    if img.ndim == 3 and img.shape[-1] == 3:
        return Image.fromarray(img, 'RGB')

    image = img
    if image.ndim == 3 and image.shape[-1] == 1:
        image = np.squeeze(image, -1)
    assert image.ndim == 2  # серое изображение
    pillow_image = Image.fromarray(image, 'L').convert('RGB')
    return pillow_image


def get_contours_and_boxes(seg_map, min_area=10):
    _seg_map = seg_map

    _, cnts, _ = cv2.findContours(np.array(_seg_map, dtype=np.uint8),
                                  mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE)

    cnts = list(filter(lambda cnt: cv2.contourArea(cnt) > min_area, cnts))
    rects = [cv2.minAreaRect(cnt) for cnt in cnts]
    boxes = [cv2.boxPoints(rect).reshape((8,)) for rect in rects]
    assert len(boxes) == len(cnts)

    return cnts, boxes


def rescale_bbox(bbox, xscale, yscale):
    scale = np.array([xscale, yscale] * 4)
    return (bbox * scale).astype(int)


def rescale_bboxes(bboxes, xscale, yscale):
    if not bboxes:
        return bboxes
    scale = np.array([xscale, yscale] * 4)
    return (bboxes * scale).astype(int)


def get_polygon_sides_lengths(poly):
    """
    возвращает длины сторон многоугольника, заданного своими вершинами
    :param poly:
    :return:
    """
    return [np.sum((poly[i] - poly[(i + 1) % len(poly)]) ** 2) ** 0.5 for i in range(len(poly))]


def is_quad_square(quad, treshold=0.1):
    sides_lengths = get_polygon_sides_lengths(quad)
    return 1. * (max(sides_lengths) - min(sides_lengths)) / max(sides_lengths) < treshold


def find_corresponding_image(images_folder_path, fname_without_ext):
    """
    Находит изображение с тем же именем, что и файл разметки, если такого нет кидает исключение
    :param images_folder_path:
    :param fname_without_ext:
    :return:
    """
    for image_ext in ('.png', '.tiff', '.tif', '.bmp', '.jpg'):
        candidate_fname = fname_without_ext + image_ext
        if os.path.exists(os.path.join(images_folder_path, candidate_fname)):
            return os.path.join(images_folder_path, candidate_fname)
    raise ValueError("Image corresponding to fname {} not found (skipping markup)".format(fname_without_ext))


def extract_bboxes_and_object_types(image_markup, net_config, object_types_format="name"):
    """
    разделяет разметку на прямоугольники и типы этих прямоугольников
    :param image_markup: разметка изображения - список ObjectMarkup
    :param net_config:
    :param object_types_format: "name" - возвращать названия классов (строчку), "id" - возвращать id классов (int)
    :return: bboxes, object_types
    """
    bboxes = [m.bbox for m in image_markup]
    if net_config.is_classification_supported():
        if object_types_format == "id":
            obj_types = [m.object_type for m in image_markup]
        elif object_types_format == "name":
            obj_types = [net_config.get_class_name(m.object_type) for m in image_markup]
        else:
            raise ValueError("Unsupported object type format")
    else:
        obj_types = None
    return bboxes, obj_types


def np_softmax(logits, axis=-1):
    x = logits - np.max(logits, axis=axis, keepdims=True)
    x = np.exp(x)
    return x / np.sum(x, axis=axis, keepdims=True)
