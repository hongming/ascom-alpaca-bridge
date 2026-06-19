from __future__ import annotations

import struct
import zlib
from datetime import date, datetime
import logging
from threading import Thread
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from .alpaca_response import empty_response, error_response, next_server_transaction_id, parse_client_transaction_id, value_response
from .ascom_driver import AscomDriverError, CameraDriver
from .config import CameraConfig
from .telescope_routes import _bool_value, _get_form_value, _json_error, _jsonable, _ok_or_error


GET_PROPERTIES = {
    "name": "Name",
    "description": "Description",
    "driverinfo": "DriverInfo",
    "driverversion": "DriverVersion",
    "interfaceversion": "InterfaceVersion",
    "connected": "Connected",
    "connecting": "Connecting",
    "devicestate": "DeviceState",
    "bayeroffsetx": "BayerOffsetX",
    "bayeroffsety": "BayerOffsetY",
    "binx": "BinX",
    "biny": "BinY",
    "ccdtemperature": "CCDTemperature",
    "camerastate": "CameraState",
    "cameraxsize": "CameraXSize",
    "cameraysize": "CameraYSize",
    "canabortexposure": "CanAbortExposure",
    "canasymmetricbin": "CanAsymmetricBin",
    "canfastreadout": "CanFastReadout",
    "cangetcoolerpower": "CanGetCoolerPower",
    "canpulseguide": "CanPulseGuide",
    "cansetccdtemperature": "CanSetCCDTemperature",
    "canstopexposure": "CanStopExposure",
    "cooleron": "CoolerOn",
    "coolerpower": "CoolerPower",
    "electronsperadu": "ElectronsPerADU",
    "exposuremax": "ExposureMax",
    "exposuremin": "ExposureMin",
    "exposureresolution": "ExposureResolution",
    "fastreadout": "FastReadout",
    "fullwellcapacity": "FullWellCapacity",
    "gain": "Gain",
    "gainmax": "GainMax",
    "gainmin": "GainMin",
    "gains": "Gains",
    "hasshutter": "HasShutter",
    "heatsinktemperature": "HeatSinkTemperature",
    "imageready": "ImageReady",
    "ispulseguiding": "IsPulseGuiding",
    "lastexposureduration": "LastExposureDuration",
    "lastexposurestarttime": "LastExposureStartTime",
    "maxadu": "MaxADU",
    "maxbinx": "MaxBinX",
    "maxbiny": "MaxBinY",
    "numx": "NumX",
    "numy": "NumY",
    "offset": "Offset",
    "offsetmax": "OffsetMax",
    "offsetmin": "OffsetMin",
    "offsets": "Offsets",
    "percentcompleted": "PercentCompleted",
    "pixelsizex": "PixelSizeX",
    "pixelsizey": "PixelSizeY",
    "readoutmode": "ReadoutMode",
    "readoutmodes": "ReadoutModes",
    "sensorname": "SensorName",
    "sensortype": "SensorType",
    "setccdtemperature": "SetCCDTemperature",
    "startx": "StartX",
    "starty": "StartY",
    "subexposureduration": "SubExposureDuration",
}


LOG = logging.getLogger(__name__)

SUPPORTED_ACTIONS: list[str] = []
ALPACA_NOT_CONNECTED = 0x407

CONNECTED_OPTIONAL_MEMBERS = {
    "name",
    "description",
    "driverinfo",
    "driverversion",
    "interfaceversion",
    "connected",
    "connecting",
    "devicestate",
    "supportedactions",
    "canabortexposure",
    "canasymmetricbin",
    "canfastreadout",
    "cangetcoolerpower",
    "canpulseguide",
    "cansetccdtemperature",
    "canstopexposure",
}


SET_PROPERTIES = {
    "binx": ("BinX", int),
    "biny": ("BinY", int),
    "cooleron": ("CoolerOn", _bool_value),
    "fastreadout": ("FastReadout", _bool_value),
    "gain": ("Gain", int),
    "numx": ("NumX", int),
    "numy": ("NumY", int),
    "offset": ("Offset", int),
    "readoutmode": ("ReadoutMode", int),
    "setccdtemperature": ("SetCCDTemperature", float),
    "startx": ("StartX", int),
    "starty": ("StartY", int),
    "subexposureduration": ("SubExposureDuration", float),
}

IMAGE_METADATA_PROPERTIES = (
    "MetadataVersion",
    "ImageElementType",
    "TransmissionElementType",
    "Rank",
    "Dimension1",
    "Dimension2",
    "Dimension3",
)

IMAGE_ELEMENT_UNKNOWN = 0
IMAGE_ELEMENT_INT16 = 1
IMAGE_ELEMENT_INT32 = 2
IMAGE_ELEMENT_DOUBLE = 3
IMAGE_ELEMENT_SINGLE = 4
IMAGE_ELEMENT_UINT64 = 5
IMAGE_ELEMENT_BYTE = 6
IMAGE_ELEMENT_INT64 = 7
IMAGE_ELEMENT_UINT16 = 8
SUPPORTED_IMAGE_ELEMENT_TYPES = {
    IMAGE_ELEMENT_INT16,
    IMAGE_ELEMENT_INT32,
    IMAGE_ELEMENT_DOUBLE,
    IMAGE_ELEMENT_SINGLE,
    IMAGE_ELEMENT_UINT64,
    IMAGE_ELEMENT_BYTE,
    IMAGE_ELEMENT_INT64,
    IMAGE_ELEMENT_UINT16,
}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
FITS_BLOCK_SIZE = 2880
IMAGEBYTES_HEADER_SIZE = 44


def _ensure_connected(driver: CameraDriver, member: str) -> None:
    if member.lower() in CONNECTED_OPTIONAL_MEMBERS:
        return
    if not bool(driver.get("Connected")):
        raise AscomDriverError(
            f"Camera must be connected before accessing '{member}'",
            error_number=ALPACA_NOT_CONNECTED,
        )


def _camera_jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return list(value)
    if isinstance(value, bytearray):
        return list(value)
    metadata = {
        name: _camera_jsonable(getattr(value, name))
        for name in IMAGE_METADATA_PROPERTIES
        if hasattr(value, name)
    }
    if metadata:
        return metadata
    return _jsonable(value)


def _get_image_array(driver: CameraDriver, raw: bool = False) -> Any:
    if raw:
        try:
            return driver.get("ImageArrayRaw")
        except AscomDriverError as exc:
            if "imagearrayraw" not in str(exc).lower():
                raise
    return driver.get("ImageArray")


def _is_missing_member_error(exc: AscomDriverError, member: str) -> bool:
    message = str(exc).lower()
    member_key = member.lower()
    return member_key in message or "no attribute" in message or "unknown name" in message


def _is_no_image_error(exc: AscomDriverError) -> bool:
    message = str(exc).lower()
    return (
        exc.error_number == 0x40B
        or "no image available" in message
        or "no image data" in message
        or "parameter name: source" in message
        or "参数名: source" in message
    )


def _no_image_response(request: Request) -> JSONResponse:
    return JSONResponse(
        error_response(
            0x40B,
            "No camera image is available yet. Start an exposure and wait for ImageReady=true before preview/download.",
            request,
        )
    )


def _array_dimensions(value: Any) -> list[int]:
    if isinstance(value, (str, bytes, bytearray)) or value is None:
        return []
    try:
        length = len(value)
    except TypeError:
        return []
    if length == 0:
        return [0]
    try:
        first = value[0]
    except Exception:
        return [length]
    return [length, *_array_dimensions(first)]


def _first_scalar(value: Any) -> Any:
    current = value
    while True:
        if isinstance(current, (str, bytes, bytearray)) or current is None:
            return current
        try:
            if len(current) == 0:
                return None
            current = current[0]
        except Exception:
            return current


def _image_element_type(value: Any) -> int:
    scalar = _first_scalar(value)
    if isinstance(scalar, float):
        return IMAGE_ELEMENT_DOUBLE
    if isinstance(scalar, int):
        if -32768 <= scalar <= 32767:
            return IMAGE_ELEMENT_INT16
        return IMAGE_ELEMENT_INT32
    return IMAGE_ELEMENT_UNKNOWN


def _infer_image_metadata(value: Any) -> dict[str, int]:
    dimensions = _array_dimensions(value)
    rank = len(dimensions)
    if rank >= 2:
        dimension1 = dimensions[1]
        dimension2 = dimensions[0]
    elif rank == 1:
        dimension1 = dimensions[0]
        dimension2 = 0
    else:
        dimension1 = 0
        dimension2 = 0
    dimension3 = dimensions[2] if rank >= 3 else 0
    element_type = _image_element_type(value)
    return {
        "MetadataVersion": 1,
        "ImageElementType": element_type,
        "TransmissionElementType": element_type,
        "Rank": rank,
        "Dimension1": dimension1,
        "Dimension2": dimension2,
        "Dimension3": dimension3,
    }


def _int_or_default(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _metadata_type(value: Any, fallback: int) -> int:
    image_type = _int_or_default(value, IMAGE_ELEMENT_UNKNOWN)
    if image_type in SUPPORTED_IMAGE_ELEMENT_TYPES:
        return image_type
    if fallback in SUPPORTED_IMAGE_ELEMENT_TYPES:
        return fallback
    return IMAGE_ELEMENT_INT32


def _positive_metadata_dimension(value: Any, fallback: Any) -> int:
    dimension = _int_or_default(value, 0)
    if dimension > 0:
        return dimension
    return _int_or_default(fallback, 0)


def _normalize_image_metadata(
    value: Any,
    fallback: dict[str, Any] | None = None,
    configured_dimensions: tuple[int, int] | None = None,
) -> dict[str, int] | None:
    if value is None:
        return fallback
    if not isinstance(value, dict):
        return fallback

    fallback = fallback or {}
    fallback_image_type = _int_or_default(fallback.get("ImageElementType"), IMAGE_ELEMENT_INT32)
    image_type = _metadata_type(value.get("ImageElementType"), fallback_image_type)
    fallback_transmission_type = _int_or_default(
        fallback.get("TransmissionElementType"),
        image_type,
    )
    transmission_type = _metadata_type(value.get("TransmissionElementType"), fallback_transmission_type)
    if transmission_type == IMAGE_ELEMENT_UNKNOWN:
        transmission_type = image_type

    dimension1 = _positive_metadata_dimension(value.get("Dimension1"), fallback.get("Dimension1"))
    dimension2 = _positive_metadata_dimension(value.get("Dimension2"), fallback.get("Dimension2"))
    if configured_dimensions is not None:
        configured_x, configured_y = configured_dimensions
        if dimension1 <= 0:
            dimension1 = configured_x
        if dimension2 <= 0:
            dimension2 = configured_y
    dimension3 = _positive_metadata_dimension(value.get("Dimension3"), fallback.get("Dimension3"))
    rank = _positive_metadata_dimension(value.get("Rank"), fallback.get("Rank"))
    if rank <= 0:
        rank = 3 if dimension3 > 0 else 2

    return {
        "MetadataVersion": _int_or_default(value.get("MetadataVersion"), 1),
        "ImageElementType": image_type,
        "TransmissionElementType": transmission_type,
        "Rank": rank,
        "Dimension1": max(0, dimension1),
        "Dimension2": max(0, dimension2),
        "Dimension3": max(0, dimension3),
    }


def _configured_image_dimensions(driver: CameraDriver) -> tuple[int, int] | None:
    try:
        width = int(driver.get("NumX"))
        height = int(driver.get("NumY"))
    except (TypeError, ValueError, AscomDriverError):
        return None
    if width <= 0 or height <= 0:
        return None
    return width, height


def _is_sequence(value: Any) -> bool:
    return not isinstance(value, (str, bytes, bytearray)) and hasattr(value, "__len__") and hasattr(value, "__getitem__")


def _numeric_value(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _pixel_luminance(pixel: Any) -> float:
    if _is_sequence(pixel):
        channels = [_numeric_value(pixel[index]) for index in range(min(len(pixel), 3))]
        if len(channels) >= 3:
            return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
        if channels:
            return channels[0]
        return 0.0
    return _numeric_value(pixel)


def _image_to_luminance_rows(value: Any) -> list[list[float]]:
    if not _is_sequence(value) or len(value) == 0:
        raise ValueError("ImageArray is empty or not an array")

    first = value[0]
    if not _is_sequence(first):
        return [[_pixel_luminance(value[index]) for index in range(len(value))]]

    rows: list[list[float]] = []
    for y in range(len(value)):
        row_value = value[y]
        if not _is_sequence(row_value):
            rows.append([_pixel_luminance(row_value)])
            continue
        rows.append([_pixel_luminance(row_value[x]) for x in range(len(row_value))])

    width = max((len(row) for row in rows), default=0)
    if width == 0:
        raise ValueError("ImageArray has no pixels")
    return [row + [0.0] * (width - len(row)) for row in rows]


def _percentile(sorted_values: list[float], fraction: float) -> float:
    if not sorted_values:
        return 0.0
    index = round((len(sorted_values) - 1) * fraction)
    return sorted_values[max(0, min(index, len(sorted_values) - 1))]


def _auto_stretch_rows(rows: list[list[float]]) -> list[bytes]:
    values = sorted(pixel for row in rows for pixel in row)
    low = _percentile(values, 0.01)
    high = _percentile(values, 0.99)
    if high <= low:
        low = values[0]
        high = values[-1]
    if high <= low:
        return [bytes(0 for _pixel in row) for row in rows]

    scale = 255.0 / (high - low)
    stretched_rows = []
    for row in rows:
        stretched = []
        for pixel in row:
            value = int(round((pixel - low) * scale))
            stretched.append(max(0, min(255, value)))
        stretched_rows.append(bytes(stretched))
    return stretched_rows


def _crop_empty_borders(rows: list[list[float]]) -> list[list[float]]:
    height = len(rows)
    width = len(rows[0]) if rows else 0
    if width <= 1 or height <= 1:
        return rows

    values = [pixel for row in rows for pixel in row]
    low = min(values)
    high = max(values)
    if high <= low:
        return rows
    threshold = low + (high - low) * 0.001

    used_rows = [index for index, row in enumerate(rows) if any(pixel > threshold for pixel in row)]
    if not used_rows:
        return rows
    used_columns = [
        index
        for index in range(width)
        if any(row[index] > threshold for row in rows)
    ]
    if not used_columns:
        return rows

    top = min(used_rows)
    bottom = max(used_rows)
    left = min(used_columns)
    right = max(used_columns)
    if top == 0 and bottom == height - 1 and left == 0 and right == width - 1:
        return rows

    cropped_width = right - left + 1
    cropped_height = bottom - top + 1
    if cropped_width <= 0 or cropped_height <= 0:
        return rows
    return [row[left : right + 1] for row in rows[top : bottom + 1]]


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(chunk_type)
    checksum = zlib.crc32(data, checksum) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum)


def _grayscale_png(rows: list[bytes]) -> bytes:
    height = len(rows)
    width = len(rows[0]) if rows else 0
    if width <= 0 or height <= 0:
        raise ValueError("ImageArray has no pixels")

    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    scanlines = b"".join(b"\x00" + row for row in rows)
    return (
        PNG_SIGNATURE
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(scanlines))
        + _png_chunk(b"IEND", b"")
    )


def _image_array_to_png(value: Any, *, crop: bool = True) -> bytes:
    rows = _preview_luminance_rows(value) if crop else _image_to_luminance_rows(value)
    return _grayscale_png(_auto_stretch_rows(rows))


def _preview_luminance_rows(value: Any) -> list[list[float]]:
    return _crop_empty_borders(_image_to_luminance_rows(value))


def _pad_fits_block(data: bytes, fill: bytes = b" ") -> bytes:
    remainder = len(data) % FITS_BLOCK_SIZE
    if remainder == 0:
        return data
    return data + fill * (FITS_BLOCK_SIZE - remainder)


def _fits_card(keyword: str, value: Any = None, comment: str = "") -> str:
    if value is None:
        card = keyword
    elif isinstance(value, bool):
        rendered = "T" if value else "F"
        card = f"{keyword:<8}= {rendered:>20}"
    elif isinstance(value, str):
        card = f"{keyword:<8}= {value!r:>20}"
    else:
        card = f"{keyword:<8}= {value:>20}"
    if comment:
        card = f"{card} / {comment}"
    return card[:80].ljust(80)


def _fits_header(cards: list[str]) -> bytes:
    return _pad_fits_block("".join([*cards, "END".ljust(80)]).encode("ascii"))


def _choose_fits_format(values: list[float]) -> tuple[int, str, float, float]:
    integer_like = all(float(value).is_integer() for value in values)
    minimum = min(values)
    maximum = max(values)
    if integer_like and 0 <= minimum and maximum <= 65535:
        return 16, ">h", 1.0, 32768.0
    if integer_like and -32768 <= minimum and maximum <= 32767:
        return 16, ">h", 1.0, 0.0
    if integer_like and -2147483648 <= minimum and maximum <= 2147483647:
        return 32, ">i", 1.0, 0.0
    return -64, ">d", 1.0, 0.0


def _fits_data(rows: list[list[float]], bitpix: int, pack_format: str, bzero: float) -> bytes:
    chunks = []
    for row in rows:
        for pixel in row:
            stored = pixel - bzero
            if bitpix > 0:
                chunks.append(struct.pack(pack_format, int(round(stored))))
            else:
                chunks.append(struct.pack(pack_format, float(stored)))
    return _pad_fits_block(b"".join(chunks), fill=b"\0")


def _image_array_to_fits(value: Any) -> bytes:
    rows = _image_to_luminance_rows(value)
    height = len(rows)
    width = len(rows[0]) if rows else 0
    if width <= 0 or height <= 0:
        raise ValueError("ImageArray has no pixels")

    values = [pixel for row in rows for pixel in row]
    bitpix, pack_format, bscale, bzero = _choose_fits_format(values)
    cards = [
        _fits_card("SIMPLE", True),
        _fits_card("BITPIX", bitpix),
        _fits_card("NAXIS", 2),
        _fits_card("NAXIS1", width),
        _fits_card("NAXIS2", height),
    ]
    if bscale != 1.0:
        cards.append(_fits_card("BSCALE", bscale))
    if bzero != 0.0:
        cards.append(_fits_card("BZERO", bzero))
    cards.extend(
        [
            _fits_card("ORIGIN", "ASCOM Alpaca Bridge"),
            _fits_card("COMMENT", "Generated from ASCOM ImageArray"),
        ]
    )
    return _fits_header(cards) + _fits_data(rows, bitpix, pack_format, bzero)


def _image_array_to_imagebytes(value: Any, request: Request) -> bytes:
    rows = _image_to_luminance_rows(value)
    height = len(rows)
    width = len(rows[0]) if rows else 0
    if width <= 0 or height <= 0:
        raise ValueError("ImageArray has no pixels")

    values = [pixel for row in rows for pixel in row]
    transmission_type = IMAGE_ELEMENT_DOUBLE if any(isinstance(pixel, float) and not pixel.is_integer() for pixel in values) else IMAGE_ELEMENT_INT32
    image_type = transmission_type
    pack_format = "<d" if transmission_type == IMAGE_ELEMENT_DOUBLE else "<i"
    payload = b"".join(
        struct.pack(pack_format, float(pixel) if transmission_type == IMAGE_ELEMENT_DOUBLE else int(round(pixel)))
        for pixel in values
    )
    header = struct.pack(
        "<11i",
        1,
        0,
        parse_client_transaction_id(request),
        next_server_transaction_id(),
        IMAGEBYTES_HEADER_SIZE,
        image_type,
        transmission_type,
        2,
        width,
        height,
        0,
    )
    return header + payload


def _accepts_imagebytes(request: Request) -> bool:
    return "application/imagebytes" in request.headers.get("accept", "").lower()


def create_camera_router(config: CameraConfig, driver: CameraDriver) -> APIRouter:
    router = APIRouter(prefix=f"/api/v1/camera/{config.device_number}")
    last_image_metadata: dict[str, Any] = {"value": None}
    effective_dimensions: dict[str, tuple[int, int] | None] = {"value": None}

    def update_effective_dimensions(metadata: dict[str, Any] | None) -> None:
        if not metadata:
            return
        width = _int_or_default(metadata.get("Dimension1"), 0)
        height = _int_or_default(metadata.get("Dimension2"), 0)
        if width > 0 and height > 0:
            effective_dimensions["value"] = (width, height)

    def refresh_image_metadata_from_driver() -> None:
        try:
            metadata = _normalize_image_metadata(
                _camera_jsonable(driver.get("ImageArrayInfo")),
                last_image_metadata["value"],
                _configured_image_dimensions(driver),
            )
        except AscomDriverError:
            return
        last_image_metadata["value"] = metadata
        update_effective_dimensions(metadata)

    def set_last_image_metadata(metadata: dict[str, Any] | None) -> None:
        last_image_metadata["value"] = metadata
        update_effective_dimensions(metadata)

    @router.get("/supportedactions")
    def supported_actions(request: Request) -> dict:
        return value_response(SUPPORTED_ACTIONS, request)

    @router.get("/connecting")
    def connecting(request: Request) -> Any:
        try:
            return value_response(bool(driver.get("Connecting")), request)
        except AscomDriverError:
            return value_response(False, request)

    @router.get("/imagearray")
    def image_array(request: Request) -> Any:
        try:
            _ensure_connected(driver, "imagearray")
            image = _get_image_array(driver)
            json_image = _camera_jsonable(image)
            set_last_image_metadata(_normalize_image_metadata(_infer_image_metadata(json_image)))
            if _accepts_imagebytes(request):
                return Response(
                    content=_image_array_to_imagebytes(json_image, request),
                    media_type="application/imagebytes",
                )
            return value_response(json_image, request)
        except AscomDriverError as exc:
            if _is_no_image_error(exc):
                return _no_image_response(request)
            return _json_error(exc, request)

    @router.get("/imagearrayraw")
    def image_array_raw(request: Request) -> Any:
        try:
            _ensure_connected(driver, "imagearrayraw")
            image = _get_image_array(driver, raw=True)
            json_image = _camera_jsonable(image)
            set_last_image_metadata(_normalize_image_metadata(_infer_image_metadata(json_image)))
            return value_response(json_image, request)
        except AscomDriverError as exc:
            if _is_no_image_error(exc):
                return _no_image_response(request)
            return _json_error(exc, request)

    @router.get("/imagearrayinfo")
    def image_array_info(request: Request) -> Any:
        try:
            _ensure_connected(driver, "imagearrayinfo")
            metadata = _normalize_image_metadata(
                _camera_jsonable(driver.get("ImageArrayInfo")),
                last_image_metadata["value"],
                _configured_image_dimensions(driver),
            )
            set_last_image_metadata(metadata)
            return value_response(metadata, request)
        except AscomDriverError as exc:
            if _is_missing_member_error(exc, "ImageArrayInfo"):
                return value_response(last_image_metadata["value"], request)
            return _json_error(exc, request)

    @router.get("/imagearray.png")
    def image_array_png(request: Request) -> Any:
        try:
            _ensure_connected(driver, "imagearray.png")
            image = _get_image_array(driver)
            json_image = _camera_jsonable(image)
            set_last_image_metadata(_normalize_image_metadata(_infer_image_metadata(json_image)))
            png = _image_array_to_png(json_image)
            headers = {"Content-Disposition": 'inline; filename="camera-image.png"'}
            return Response(content=png, media_type="image/png", headers=headers)
        except ValueError as exc:
            return JSONResponse(error_response(0x400, str(exc), request))
        except AscomDriverError as exc:
            if _is_no_image_error(exc):
                return _no_image_response(request)
            return _json_error(exc, request)

    @router.get("/imagearray.raw.png")
    def image_array_raw_png(request: Request) -> Any:
        try:
            _ensure_connected(driver, "imagearray.raw.png")
            image = _get_image_array(driver)
            json_image = _camera_jsonable(image)
            set_last_image_metadata(_normalize_image_metadata(_infer_image_metadata(json_image)))
            png = _image_array_to_png(json_image, crop=False)
            headers = {"Content-Disposition": 'inline; filename="camera-image-raw.png"'}
            return Response(content=png, media_type="image/png", headers=headers)
        except ValueError as exc:
            return JSONResponse(error_response(0x400, str(exc), request))
        except AscomDriverError as exc:
            if _is_no_image_error(exc):
                return _no_image_response(request)
            return _json_error(exc, request)

    @router.get("/imagearray.fits")
    def image_array_fits(request: Request) -> Any:
        try:
            _ensure_connected(driver, "imagearray.fits")
            image = _get_image_array(driver)
            json_image = _camera_jsonable(image)
            set_last_image_metadata(_normalize_image_metadata(_infer_image_metadata(json_image)))
            fits = _image_array_to_fits(json_image)
            headers = {"Content-Disposition": 'attachment; filename="camera-image.fits"'}
            return Response(content=fits, media_type="application/fits", headers=headers)
        except ValueError as exc:
            return JSONResponse(error_response(0x400, str(exc), request))
        except AscomDriverError as exc:
            if _is_no_image_error(exc):
                return _no_image_response(request)
            return _json_error(exc, request)

    @router.get("/{member}")
    def get_member(member: str, request: Request) -> Any:
        property_name = GET_PROPERTIES.get(member.lower())
        if property_name is None:
            return JSONResponse(error_response(0x400, f"Unknown or unsupported Camera member: {member}", request))
        try:
            _ensure_connected(driver, member)
            if member.lower() in {"cameraxsize", "numx"} and effective_dimensions["value"] is not None:
                return value_response(effective_dimensions["value"][0], request)
            if member.lower() in {"cameraysize", "numy"} and effective_dimensions["value"] is not None:
                return value_response(effective_dimensions["value"][1], request)
            return value_response(_jsonable(driver.get(property_name)), request)
        except AscomDriverError as exc:
            return _json_error(exc, request)

    @router.put("/connected")
    async def set_connected(request: Request) -> Any:
        form = dict(await request.form())

        def set_value() -> None:
            connected = _get_form_value(form, "Connected")
            driver.set("Connected", _bool_value(connected))
            if _bool_value(connected):
                refresh_image_metadata_from_driver()

        return _ok_or_error(request, set_value)

    @router.put("/connect")
    async def connect(request: Request) -> Any:
        def connect_driver() -> None:
            driver.set("Connected", True)
            refresh_image_metadata_from_driver()

        return _ok_or_error(request, connect_driver)

    @router.put("/disconnect")
    async def disconnect(request: Request) -> Any:
        return _ok_or_error(request, lambda: driver.set("Connected", False))

    @router.put("/startexposure")
    async def start_exposure(request: Request) -> Any:
        form = dict(await request.form())
        try:
            _ensure_connected(driver, "startexposure")
            duration = float(_get_form_value(form, "Duration"))
            light = _bool_value(_get_form_value(form, "Light"))
        except (ValueError, AscomDriverError) as exc:
            if isinstance(exc, AscomDriverError):
                return _json_error(exc, request)
            return JSONResponse(error_response(0x400, str(exc), request))

        def invoke() -> None:
            try:
                driver.invoke("StartExposure", duration, light)
            except AscomDriverError as exc:
                LOG.warning("Camera StartExposure failed in background: %s", exc)

        Thread(target=invoke, daemon=True).start()
        return empty_response(request)

    @router.put("/stopexposure")
    async def stop_exposure(request: Request) -> Any:
        try:
            _ensure_connected(driver, "stopexposure")
            driver.invoke("StopExposure")
            return empty_response(request)
        except AscomDriverError as exc:
            return _json_error(exc, request)

    @router.put("/abortexposure")
    async def abort_exposure(request: Request) -> Any:
        try:
            _ensure_connected(driver, "abortexposure")
            driver.invoke("AbortExposure")
            return empty_response(request)
        except AscomDriverError as exc:
            return _json_error(exc, request)

    @router.put("/action")
    async def action(request: Request) -> Any:
        form = dict(await request.form())
        try:
            action_name = str(_get_form_value(form, "Action"))
            parameters = str(_get_form_value(form, "Parameters"))
            _ensure_connected(driver, "action")
            return value_response(_jsonable(driver.invoke("Action", action_name, parameters)), request)
        except (ValueError, AscomDriverError) as exc:
            if isinstance(exc, AscomDriverError):
                return _json_error(exc, request)
            return JSONResponse(error_response(0x400, str(exc), request))

    @router.put("/commandblind")
    async def command_blind(request: Request) -> Any:
        form = dict(await request.form())

        def invoke() -> None:
            command = str(_get_form_value(form, "Command"))
            raw = _bool_value(_get_form_value(form, "Raw"))
            _ensure_connected(driver, "commandblind")
            driver.invoke("CommandBlind", command, raw)

        return _ok_or_error(request, invoke)

    @router.put("/commandbool")
    async def command_bool(request: Request) -> Any:
        form = dict(await request.form())
        try:
            command = str(_get_form_value(form, "Command"))
            raw = _bool_value(_get_form_value(form, "Raw"))
            _ensure_connected(driver, "commandbool")
            return value_response(bool(driver.invoke("CommandBool", command, raw)), request)
        except (ValueError, AscomDriverError) as exc:
            if isinstance(exc, AscomDriverError):
                return _json_error(exc, request)
            return JSONResponse(error_response(0x400, str(exc), request))

    @router.put("/commandstring")
    async def command_string(request: Request) -> Any:
        form = dict(await request.form())
        try:
            command = str(_get_form_value(form, "Command"))
            raw = _bool_value(_get_form_value(form, "Raw"))
            _ensure_connected(driver, "commandstring")
            return value_response(str(driver.invoke("CommandString", command, raw)), request)
        except (ValueError, AscomDriverError) as exc:
            if isinstance(exc, AscomDriverError):
                return _json_error(exc, request)
            return JSONResponse(error_response(0x400, str(exc), request))

    @router.put("/{member}")
    async def set_member(member: str, request: Request) -> Any:
        member_key = member.lower()
        setting = SET_PROPERTIES.get(member_key)
        if setting is None:
            return JSONResponse(error_response(0x400, f"Unsupported Camera member in current phase: {member}", request))

        property_name, converter = setting
        form = dict(await request.form())

        def set_value() -> None:
            _ensure_connected(driver, member)
            value = _get_form_value(form, property_name, member)
            driver.set(property_name, converter(value))

        return _ok_or_error(request, set_value)

    return router
