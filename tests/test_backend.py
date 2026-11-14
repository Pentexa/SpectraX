import hashlib
import json
from io import BytesIO
from pathlib import Path
from urllib.error import URLError

import numpy as np
import pytest
from astropy.coordinates import SkyCoord
from astropy.io import fits
from fastapi.testclient import TestClient

from apps.api.main import create_app
from pipeline.benchmark_barnard import benchmark
from pipeline.catalog import ArchiveFile, Position, load_manifest
from pipeline.compare import output_grid
from pipeline.images import read_image
from pipeline.ingest import fetch

POSITION = {'ra': 269.45, 'dec': 4.7, 'fov': 0.025}
MANIFEST = Path(__file__).resolve().parents[1] / 'data/manifests/spherex-dr1.json'


@pytest.fixture
def test_data(tmp_path):
    wcs, shape = output_grid(Position(**POSITION), 0.001)
    header = wcs.to_header()
    header['BUNIT'] = 'MJy/sr'
    products = []
    for i, epoch in enumerate(('a', 'b', 'wrong-band', 'invalid', 'different-unit', 'missing')):
        signal = np.zeros(shape)
        signal[12, 11 + 2 * min(i, 1)] = 10
        signal[9, 9] = np.nan
        signal[8, 8] = 10000
        flag = np.zeros(shape, dtype=np.int32)
        flag[8, 8] = 4
        mask = np.zeros(shape, dtype=np.uint8)
        mask[7, 7] = 1
        header['MJD-OBS'] = 61000 + i
        if epoch == 'different-unit':
            header['BUNIT'] = 'Jy/sr'
            signal *= 1e6
        path = tmp_path / f'{epoch}.fits'
        if epoch == 'invalid':
            path.write_bytes(b'invalid FITS')
        elif epoch != 'missing':
            fits.HDUList([
                fits.PrimaryHDU(signal, header=header),
                fits.ImageHDU(np.full(shape, 4.0 if epoch != 'different-unit' else 4e12), name='VARIANCE'),
                fits.ImageHDU(flag, name='FLAGS'),
                fits.ImageHDU(mask, name='MASK'),
            ]).writeto(path)
        data = path.read_bytes() if path.exists() else b'missing'
        products.append(dict(epoch=epoch, source='test fixture', release='test', observation_id=epoch,
                             observation_start_mjd=61000+i, observation_end_mjd=61000+i,
                             access='https://example.invalid/images.fits', size_bytes=len(data),
                             sha256=hashlib.sha256(data).hexdigest(), filename=path.name,
                             calibration='fixture', processing_history=['Synthetic FITS fixture'],
                             coverage=POSITION, flags='test mask and flags',
                             band='other' if epoch == 'wrong-band' else 'test-band', spectral_wcs='fixed'))
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'observations': products}), encoding='utf-8')
    return manifest, tmp_path


@pytest.fixture
def client(test_data):
    with TestClient(create_app(*test_data)) as client:
        yield client


def compare(client, epoch_a='a', epoch_b='b', mode='difference', **coordinates):
    return client.get('/api/compare', params={**POSITION, **coordinates, 'epoch_a': epoch_a,
                                              'epoch_b': epoch_b, 'mode': mode})


def test_world_pixel_round_trip(test_data):
    manifest, root = test_data
    image = read_image(root, load_manifest(manifest).observations[0])
    point = SkyCoord(POSITION['ra'], POSITION['dec'], unit='deg')
    x, y = image.wcs.world_to_pixel(point)
    assert (x, y) == pytest.approx((12, 12))
    assert image.wcs.pixel_to_world(x, y).separation(point).arcsec < 1e-6


def test_difference_sign_uncertainty_and_mask(client):
    response = compare(client)
    assert response.status_code == 200
    payload = response.json()
    result = payload['images']['result']
    assert result[12][11] == -10
    assert result[12][13] == 10
    for y, x in [(7, 7), (8, 8), (9, 9)]:
        assert result[y][x] is None
    assert payload['flags']['a'][8][8] == 4
    assert payload['images']['snr'][12][13] == pytest.approx(10 / np.sqrt(8))
    assert payload['measurement']['uncertainty'] == pytest.approx(np.sqrt(8))
    assert payload['display']['min'] == -payload['display']['max']


def test_same_image_difference(client):
    payload = compare(client, epoch_b='a').json()
    assert {value for row in payload['images']['result'] for value in row} == {0.0, None}
    assert payload['measurement']['uncertainty'] == 0
    assert payload['images']['snr'] is None


def test_wcs_registration_aligns_a_stationary_source(test_data):
    manifest_path, root = test_data
    manifest = load_manifest(manifest_path)
    a, b = manifest.observations[:2]
    # B records the same sky location two pixels to the right because its WCS moved too.
    path = root / b.filename
    with fits.open(path, mode='update') as hdus:
        hdus[0].header['CRPIX1'] += 2
    with TestClient(create_app(manifest_path, root)) as client:
        response = compare(client, a.epoch, b.epoch)
    assert response.status_code == 200
    payload = response.json()
    assert payload['images']['a'][12][11] == 10
    assert payload['images']['b'][12][11] == 10
    assert payload['images']['result'][12][11] == 0


@pytest.mark.parametrize('shift_pixels', [0, 1.25])
def test_registration_checks_shared_peaks(test_data, shift_pixels):
    manifest_path, root = test_data
    a, b = load_manifest(manifest_path).observations[:2]
    peaks = [(4, 5), (7, 18), (12, 12), (16, 4), (19, 18)]
    for observation, shift in ((a, 0), (b, shift_pixels)):
        with fits.open(root / observation.filename, mode='update') as hdus:
            hdus[0].data[:] = 0
            for y, x in peaks:
                hdus[0].data[y, x] = 25
            hdus['FLAGS'].data[:] = 0
            hdus['MASK'].data[:] = 0
            hdus[0].header['CRPIX1'] += shift
    with TestClient(create_app(manifest_path, root)) as client:
        difference = compare(client)
        side_by_side = compare(client, mode='side_by_side')
    report = side_by_side.json()['alignment']['registration']
    assert report['used_sources'] == len(peaks)
    assert report['median_offset_arcsec']['magnitude'] == pytest.approx(shift_pixels * 3.6, abs=0.02)
    if shift_pixels:
        assert difference.status_code == 422
        assert difference.json()['error']['details']['status'] == 'failed'
    else:
        assert difference.json()['alignment']['astrometric_offset_verified'] is True


@pytest.mark.parametrize(('mode', 'value', 'uncertainty'), [('sum', 10, np.sqrt(8)), ('stack', 5, np.sqrt(2))])
def test_arithmetic_and_unit_conversion(client, mode, value, uncertainty):
    payload = compare(client, epoch_b='different-unit', mode=mode).json()
    assert payload['images']['result'][12][13] == pytest.approx(value)
    assert payload['images']['uncertainty'][12][13] == pytest.approx(uncertainty)
    assert payload['units']['a'] == payload['units']['b']


@pytest.mark.parametrize(('epoch', 'status', 'code'), [
    ('wrong-band', 422, 'incompatible_epochs'), ('invalid', 422, 'invalid_fits'),
    ('missing', 503, 'data_unavailable'), ('unknown', 404, 'unknown_epoch'),
])
def test_epoch_errors(client, epoch, status, code):
    response = compare(client, epoch_b=epoch)
    assert response.status_code == status
    assert response.json()['error']['code'] == code


def test_health_validation_and_no_cube(client):
    assert client.get('/api/health').json() == {'status': 'ok', 'products': 6, 'available_locally': 5}
    assert len(client.get('/api/datasets').json()['observations']) == 6
    assert compare(client, fov=9).json()['error']['code'] == 'invalid_request'
    assert compare(client, ra='NaN').json()['error']['code'] == 'invalid_request'
    assert compare(client, ra=0, dec=0).json()['error']['code'] == 'insufficient_overlap'
    response = client.get('/api/spectrum', params={'ra': 12, 'dec': 34, 'epoch': 'a'})
    assert response.status_code == 409


def test_ingest_fallback_and_idempotency(test_data, monkeypatch):
    manifest, root = test_data
    product = load_manifest(manifest).observations[0]
    file = (root / product.filename).read_bytes()
    product.full_image = ArchiveFile(access='https://example.invalid/full.fits', size_bytes=len(file),
                                     sha256=hashlib.sha256(file).hexdigest())
    requests = []

    def download(url, timeout):
        requests.append(url)
        if url == str(product.access):
            raise URLError('Unavailable')
        return BytesIO(file)

    monkeypatch.setattr('pipeline.ingest.urlopen', download)
    target = root / 'download'
    assert fetch(product, target).read_bytes() == file
    assert fetch(product, target).is_file()
    assert requests == [str(product.access), str(product.full_image.access)]


def test_real_dr1_when_downloaded():
    manifest = load_manifest(MANIFEST)
    root = MANIFEST.parent.parent / 'samples'
    if not all((root / product.filename).is_file() for product in [*manifest.observations, *manifest.cubes]):
        pytest.skip('Run planet-x-data --include-cubes to exercise public FITS samples')
    with TestClient(create_app(MANIFEST, root)) as client:
        a, b = manifest.observations
        result = compare(client, a.epoch, b.epoch, fov=0.04)
        assert result.status_code == 200
        assert result.json()['alignment']['arithmetic_valid_fraction'] > 0.8
        assert result.json()['alignment']['registration']['used_sources'] >= 5
        assert result.json()['alignment']['astrometric_offset_verified'] is True
        assert result.json()['measurement']['uncertainty'] > 0
        target = {'ra': POSITION['ra'], 'dec': POSITION['dec'], 'epoch': manifest.cubes[0].epoch}
        response = client.get('/api/spectrum', params=target)
        assert response.status_code == 200
        result = response.json()
        assert result['expected_channels'] == len(result['channels']) == 102
        assert result['available_channels'] == 100
        assert result['time_mode'] == 'multi_epoch_coadd'
        assert len([row for row in result['channels'] if row['masked'] and row['flux'] is None]) == 2
        assert result['channels'] == sorted(result['channels'], key=lambda item: item['wavelength_um'])
        assert len(client.get('/api/layers', params=target).json()['layers']) == 6
        for detector in range(1, 7):
            layer = client.get(f'/api/layers/{detector}', params={**target, 'fov': 0.025})
            assert layer.status_code == 200
            assert layer.json()['channel'] == 9


def test_barnard_quality_when_downloaded():
    manifest = load_manifest(MANIFEST)
    root = MANIFEST.parent.parent / 'samples'
    if not all((root / observation.filename).is_file() for observation in manifest.observations):
        pytest.skip('Run planet-x-data to exercise public FITS observations')
    report = benchmark(root, manifest.observations)
    assert report['status'] == 'not_testable'
    assert report['measured_offset_arcsec'] is None
    assert report['predicted_apparent_offset_arcsec']['north'] == pytest.approx(4.59, abs=0.02)
    assert {epoch['status'] for epoch in report['epochs']} <= {'outside_image', 'core_masked'}
