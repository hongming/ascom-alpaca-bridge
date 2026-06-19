from __future__ import annotations

import struct

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ascom_alpaca_bridge.camera_routes import _image_array_to_png, create_camera_router
from ascom_alpaca_bridge.ascom_driver import AscomDriverError
from ascom_alpaca_bridge.config import CameraConfig


def png_size(data: bytes) -> tuple[int, int]:
    return struct.unpack(">II", data[16:24])


def wait_for_call_count(driver: "FakeCameraDriver", name: str, count: int, timeout: float = 1.0) -> None:
    import time

    started = time.monotonic()
    while time.monotonic() - started < timeout:
        if sum(1 for call_name, _args in driver.calls if call_name == name) >= count:
            return
        time.sleep(0.01)
    raise AssertionError(f"{name} was not called {count} times")


class FakeImageMetadata:
    MetadataVersion = 1
    ImageElementType = 2
    TransmissionElementType = 2
    Rank = 2
    Dimension1 = 3
    Dimension2 = 2
    Dimension3 = 0


class FakeUnknownImageMetadata:
    MetadataVersion = 1
    ImageElementType = 0
    TransmissionElementType = 0
    Rank = 0
    Dimension1 = 0
    Dimension2 = 0
    Dimension3 = 0


class FakeCameraDriver:
    def __init__(self) -> None:
        self.values = {
            "Connected": True,
            "Connecting": False,
            "DeviceState": [],
            "CameraState": 0,
            "ImageReady": False,
            "PercentCompleted": 0,
            "CCDTemperature": -5.5,
            "CoolerOn": True,
            "CoolerPower": 42.0,
            "CameraXSize": 3000,
            "CameraYSize": 2000,
            "MaxBinX": 2,
            "MaxBinY": 2,
            "BinX": 1,
            "BinY": 1,
            "StartX": 0,
            "StartY": 0,
            "NumX": 3000,
            "NumY": 2000,
            "ExposureMin": 0.001,
            "ExposureMax": 600.0,
            "ExposureResolution": 0.001,
            "Gain": 100,
            "GainMin": 0,
            "GainMax": 300,
            "Gains": ["Low", "High"],
            "Offset": 10,
            "OffsetMin": 0,
            "OffsetMax": 50,
            "Offsets": ["Default"],
            "ReadoutMode": 0,
            "ReadoutModes": ["Normal"],
            "SensorName": "Fake Sensor",
            "SensorType": 0,
            "PixelSizeX": 3.76,
            "PixelSizeY": 3.76,
            "CanAbortExposure": True,
            "CanStopExposure": True,
            "CanSetCCDTemperature": True,
            "CanGetCoolerPower": True,
            "CanPulseGuide": False,
            "CanAsymmetricBin": False,
            "CanFastReadout": False,
            "HasShutter": True,
            "FastReadout": False,
            "SetCCDTemperature": -5.0,
            "SubExposureDuration": 0.0,
            "ImageArray": [[1, 2, 3], [4, 5, 6]],
            "ImageArrayRaw": [[1, 2, 3], [4, 5, 6]],
            "ImageArrayInfo": FakeImageMetadata(),
        }
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def get(self, name: str) -> object:
        return self.values[name]

    def set(self, name: str, value: object) -> None:
        self.values[name] = value

    def invoke(self, name: str, *args: object) -> object:
        self.calls.append((name, args))
        if name == "StartExposure":
            self.values["CameraState"] = 2
            self.values["ImageReady"] = False
            self.values["PercentCompleted"] = 0
            self.values["LastExposureDuration"] = args[0]
        if name == "StopExposure":
            self.values["CameraState"] = 0
            self.values["ImageReady"] = True
            self.values["PercentCompleted"] = 100
        if name == "AbortExposure":
            self.values["CameraState"] = 0
            self.values["ImageReady"] = False
            self.values["PercentCompleted"] = 0
        return None


def make_client() -> tuple[TestClient, FakeCameraDriver]:
    driver = FakeCameraDriver()
    app = FastAPI()
    app.include_router(create_camera_router(CameraConfig(), driver))
    return TestClient(app), driver


def test_camera_phase_one_status_properties() -> None:
    client, _driver = make_client()

    assert client.get("/api/v1/camera/0/camerastate").json()["Value"] == 0
    assert client.get("/api/v1/camera/0/imageready").json()["Value"] is False
    assert client.get("/api/v1/camera/0/ccdtemperature").json()["Value"] == -5.5
    assert client.get("/api/v1/camera/0/coolerpower").json()["Value"] == 42.0
    assert client.get("/api/v1/camera/0/cameraxsize").json()["Value"] == 3000
    assert client.get("/api/v1/camera/0/gains").json()["Value"] == ["Low", "High"]


def test_camera_connected_put() -> None:
    client, driver = make_client()

    assert client.put("/api/v1/camera/0/connected", data={"Connected": "false"}).json()["ErrorNumber"] == 0
    assert driver.values["Connected"] is False
    assert client.put("/api/v1/camera/0/connect").json()["ErrorNumber"] == 0
    assert driver.values["Connected"] is True


def test_camera_phase_two_parameter_puts() -> None:
    client, driver = make_client()

    assert client.put("/api/v1/camera/0/binx", data={"BinX": "2"}).json()["ErrorNumber"] == 0
    assert client.put("/api/v1/camera/0/biny", data={"BinY": "2"}).json()["ErrorNumber"] == 0
    assert client.put("/api/v1/camera/0/startx", data={"StartX": "10"}).json()["ErrorNumber"] == 0
    assert client.put("/api/v1/camera/0/starty", data={"StartY": "20"}).json()["ErrorNumber"] == 0
    assert client.put("/api/v1/camera/0/numx", data={"NumX": "1024"}).json()["ErrorNumber"] == 0
    assert client.put("/api/v1/camera/0/numy", data={"NumY": "768"}).json()["ErrorNumber"] == 0
    assert client.put("/api/v1/camera/0/gain", data={"Gain": "150"}).json()["ErrorNumber"] == 0
    assert client.put("/api/v1/camera/0/offset", data={"Offset": "12"}).json()["ErrorNumber"] == 0
    assert client.put("/api/v1/camera/0/readoutmode", data={"ReadoutMode": "0"}).json()["ErrorNumber"] == 0

    assert driver.values["BinX"] == 2
    assert driver.values["BinY"] == 2
    assert driver.values["StartX"] == 10
    assert driver.values["StartY"] == 20
    assert driver.values["NumX"] == 1024
    assert driver.values["NumY"] == 768
    assert driver.values["Gain"] == 150
    assert driver.values["Offset"] == 12
    assert driver.values["ReadoutMode"] == 0


def test_camera_phase_two_cooler_and_timing_puts() -> None:
    client, driver = make_client()

    assert client.put("/api/v1/camera/0/cooleron", data={"CoolerOn": "false"}).json()["ErrorNumber"] == 0
    assert client.put("/api/v1/camera/0/setccdtemperature", data={"SetCCDTemperature": "-10.5"}).json()["ErrorNumber"] == 0
    assert client.put("/api/v1/camera/0/fastreadout", data={"FastReadout": "true"}).json()["ErrorNumber"] == 0
    assert client.put("/api/v1/camera/0/subexposureduration", data={"SubExposureDuration": "0.25"}).json()["ErrorNumber"] == 0

    assert driver.values["CoolerOn"] is False
    assert driver.values["SetCCDTemperature"] == -10.5
    assert driver.values["FastReadout"] is True
    assert driver.values["SubExposureDuration"] == 0.25


def test_camera_phase_three_exposure_controls() -> None:
    client, driver = make_client()

    assert client.put("/api/v1/camera/0/startexposure", data={"Duration": "1.5", "Light": "true"}).json()["ErrorNumber"] == 0
    wait_for_call_count(driver, "StartExposure", 1)
    assert ("StartExposure", (1.5, True)) in driver.calls
    assert client.get("/api/v1/camera/0/camerastate").json()["Value"] == 2
    assert client.get("/api/v1/camera/0/imageready").json()["Value"] is False

    assert client.put("/api/v1/camera/0/stopexposure").json()["ErrorNumber"] == 0
    assert ("StopExposure", ()) in driver.calls
    assert client.get("/api/v1/camera/0/imageready").json()["Value"] is True

    assert client.put("/api/v1/camera/0/startexposure", data={"Duration": "2", "Light": "false"}).json()["ErrorNumber"] == 0
    wait_for_call_count(driver, "StartExposure", 2)
    assert ("StartExposure", (2.0, False)) in driver.calls
    assert client.put("/api/v1/camera/0/abortexposure").json()["ErrorNumber"] == 0
    assert ("AbortExposure", ()) in driver.calls
    assert client.get("/api/v1/camera/0/camerastate").json()["Value"] == 0


def test_camera_phase_four_image_download_members() -> None:
    client, _driver = make_client()

    assert client.get("/api/v1/camera/0/imagearray").json()["Value"] == [[1, 2, 3], [4, 5, 6]]
    assert client.get("/api/v1/camera/0/imagearrayraw").json()["Value"] == [[1, 2, 3], [4, 5, 6]]
    assert client.get("/api/v1/camera/0/imagearrayinfo").json()["Value"] == {
        "MetadataVersion": 1,
        "ImageElementType": 2,
        "TransmissionElementType": 2,
        "Rank": 2,
        "Dimension1": 3,
        "Dimension2": 2,
        "Dimension3": 0,
    }


def test_camera_imagearray_supports_imagebytes_response() -> None:
    client, driver = make_client()
    driver.values["NumX"] = 3
    driver.values["NumY"] = 2

    response = client.get(
        "/api/v1/camera/0/imagearray?ClientTransactionID=42",
        headers={"Accept": "application/imagebytes"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/imagebytes"
    header = struct.unpack("<11i", response.content[:44])
    assert header[0] == 1
    assert header[1] == 0
    assert header[2] == 42
    assert header[4] == 44
    assert header[5] == 2
    assert header[6] == 2
    assert header[7] == 2
    assert header[8] == 3
    assert header[9] == 2
    assert header[10] == 0
    assert struct.unpack("<6i", response.content[44:68]) == (1, 2, 3, 4, 5, 6)


def test_camera_imagebytes_keeps_output_and_transmission_types_matching_for_float_data() -> None:
    client, driver = make_client()
    driver.values["ImageArray"] = [[1.5, 2.25]]
    driver.values["NumX"] = 2
    driver.values["NumY"] = 1

    response = client.get("/api/v1/camera/0/imagearray", headers={"Accept": "application/imagebytes"})

    header = struct.unpack("<11i", response.content[:44])
    assert header[5] == 3
    assert header[6] == 3
    assert header[7] == 2
    assert header[8] == 2
    assert header[9] == 1
    assert struct.unpack("<2d", response.content[44:60]) == (1.5, 2.25)


def test_camera_imagebytes_uses_actual_image_dimensions_without_preview_crop() -> None:
    client, driver = make_client()
    driver.values["ImageArray"] = [
        [10, 20, 0, 0],
        [30, 40, 0, 0],
        [0, 0, 0, 0],
    ]

    response = client.get("/api/v1/camera/0/imagearray", headers={"Accept": "application/imagebytes"})

    header = struct.unpack("<11i", response.content[:44])
    assert header[8] == 4
    assert header[9] == 3
    assert struct.unpack("<12i", response.content[44:92]) == (
        10,
        20,
        0,
        0,
        30,
        40,
        0,
        0,
        0,
        0,
        0,
        0,
    )


def test_camera_raw_png_uses_actual_image_dimensions_without_preview_crop() -> None:
    client, driver = make_client()
    driver.values["ImageArray"] = [
        [10, 20, 0, 0],
        [30, 40, 0, 0],
        [0, 0, 0, 0],
    ]

    cropped = client.get("/api/v1/camera/0/imagearray.png")
    raw = client.get("/api/v1/camera/0/imagearray.raw.png")

    assert cropped.status_code == 200
    assert raw.status_code == 200
    assert png_size(cropped.content) == (2, 2)
    assert png_size(raw.content) == (4, 3)


def test_camera_effective_dimensions_follow_imagearrayinfo() -> None:
    client, driver = make_client()
    driver.values["ImageArrayInfo"] = FakeImageMetadata()

    assert client.put("/api/v1/camera/0/connect").json()["ErrorNumber"] == 0

    assert client.get("/api/v1/camera/0/cameraxsize").json()["Value"] == 3
    assert client.get("/api/v1/camera/0/cameraysize").json()["Value"] == 2
    assert client.get("/api/v1/camera/0/numx").json()["Value"] == 3
    assert client.get("/api/v1/camera/0/numy").json()["Value"] == 2


def test_camera_imagearrayinfo_never_returns_unknown_element_type() -> None:
    client, driver = make_client()
    driver.values["ImageArrayInfo"] = FakeUnknownImageMetadata()

    payload = client.get("/api/v1/camera/0/imagearrayinfo").json()["Value"]

    assert payload["ImageElementType"] == 2
    assert payload["TransmissionElementType"] == 2
    assert payload["Rank"] == 2
    assert payload["Dimension1"] == 3000
    assert payload["Dimension2"] == 2000


def test_camera_imagearrayinfo_uses_cached_inferred_type_when_driver_reports_unknown() -> None:
    client, driver = make_client()
    driver.values["ImageArrayInfo"] = FakeUnknownImageMetadata()

    assert client.get("/api/v1/camera/0/imagearray").json()["ErrorNumber"] == 0
    payload = client.get("/api/v1/camera/0/imagearrayinfo").json()["Value"]

    assert payload["ImageElementType"] == 1
    assert payload["TransmissionElementType"] == 1
    assert payload["Dimension1"] == 3
    assert payload["Dimension2"] == 2


def test_camera_phase_four_point_five_png_preview() -> None:
    client, _driver = make_client()

    response = client.get("/api/v1/camera/0/imagearray.png")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["content-disposition"] == 'inline; filename="camera-image.png"'
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert b"IHDR" in response.content
    assert b"IDAT" in response.content


def test_camera_png_preview_crops_empty_borders() -> None:
    png = _image_array_to_png(
        [
            [10, 20, 0, 0],
            [30, 40, 0, 0],
            [0, 0, 0, 0],
        ]
    )

    width = int.from_bytes(png[16:20], "big")
    height = int.from_bytes(png[20:24], "big")

    assert (width, height) == (2, 2)


def test_camera_phase_six_fits_download() -> None:
    client, _driver = make_client()

    response = client.get("/api/v1/camera/0/imagearray.fits")
    header = response.content[:2880].decode("ascii")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/fits"
    assert response.headers["content-disposition"] == 'attachment; filename="camera-image.fits"'
    assert len(response.content) % 2880 == 0
    assert "SIMPLE  =                    T" in header
    assert "BITPIX  =                   16" in header
    assert "NAXIS   =                    2" in header
    assert "NAXIS1  =                    3" in header
    assert "NAXIS2  =                    2" in header
    assert "BZERO   =              32768.0" in header
    assert "END" in header


def test_camera_png_preview_requires_available_image() -> None:
    client, driver = make_client()

    def get(name: str) -> object:
        if name == "ImageArray":
            raise AscomDriverError("There is no image available", error_number=0x40B)
        return driver.values[name]

    driver.get = get  # type: ignore[method-assign]

    payload = client.get("/api/v1/camera/0/imagearray.png").json()

    assert payload["ErrorNumber"] == 0x40B
    assert "wait for ImageReady=true" in payload["ErrorMessage"]


def test_camera_png_preview_treats_zwo_null_source_as_missing_image() -> None:
    client, driver = make_client()

    def get(name: str) -> object:
        if name == "ImageArray":
            raise AscomDriverError("值不能为空。\r\n参数名: source", error_number=0x40B)
        return driver.values[name]

    driver.get = get  # type: ignore[method-assign]

    payload = client.get("/api/v1/camera/0/imagearray.png").json()

    assert payload["ErrorNumber"] == 0x40B
    assert "wait for ImageReady=true" in payload["ErrorMessage"]


def test_camera_fits_download_requires_available_image() -> None:
    client, driver = make_client()

    def get(name: str) -> object:
        if name == "ImageArray":
            raise AscomDriverError("There is no image available", error_number=0x40B)
        return driver.values[name]

    driver.get = get  # type: ignore[method-assign]

    payload = client.get("/api/v1/camera/0/imagearray.fits").json()

    assert payload["ErrorNumber"] == 0x40B
    assert "wait for ImageReady=true" in payload["ErrorMessage"]


def test_camera_imagearrayraw_falls_back_to_imagearray_when_raw_member_is_missing() -> None:
    client, driver = make_client()

    def get(name: str) -> object:
        if name == "ImageArrayRaw":
            raise AscomDriverError("'FakeCameraDriver' object has no attribute 'ImageArrayRaw'")
        return driver.values[name]

    driver.get = get  # type: ignore[method-assign]

    assert client.get("/api/v1/camera/0/imagearrayraw").json()["Value"] == [[1, 2, 3], [4, 5, 6]]


def test_camera_imagearrayinfo_returns_null_then_inferred_metadata_when_member_is_missing() -> None:
    client, driver = make_client()

    def get(name: str) -> object:
        if name == "ImageArrayInfo":
            raise AscomDriverError("ASCOM.Simulator.Camera.ImageArrayInfo")
        return driver.values[name]

    driver.get = get  # type: ignore[method-assign]

    assert client.get("/api/v1/camera/0/imagearrayinfo").json()["Value"] is None
    assert client.get("/api/v1/camera/0/imagearray").json()["Value"] == [[1, 2, 3], [4, 5, 6]]
    assert client.get("/api/v1/camera/0/imagearrayinfo").json()["Value"] == {
        "MetadataVersion": 1,
        "ImageElementType": 1,
        "TransmissionElementType": 1,
        "Rank": 2,
        "Dimension1": 3,
        "Dimension2": 2,
        "Dimension3": 0,
    }
