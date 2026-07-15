"""
Minimal audioop stub for Python 3.13+ where audioop was removed.

pydub uses audioop for audio processing (fade, pan, overlay, etc.),
but simple format-conversion (load → export) does NOT call any audioop function.
This stub provides enough to let pydub import successfully.
"""
import struct
import math

_error_msg = "audioop stub: function not implemented (not needed for format conversion)"

def _int16_to_float(data, sample_width):
    """Convert PCM bytes to list of float samples (-1.0 to 1.0)."""
    fmt = {1: "b", 2: "h", 4: "i"}.get(sample_width, "h")
    count = len(data) // sample_width
    max_val = float(2 ** (sample_width * 8 - 1))
    samples = []
    for i in range(count):
        val = struct.unpack_from(fmt, data, i * sample_width)[0]
        samples.append(val / max_val)
    return samples

def _float_to_int16(samples, sample_width):
    """Convert list of float samples back to PCM bytes."""
    fmt = {1: "b", 2: "h", 4: "i"}.get(sample_width, "h")
    max_val = 2 ** (sample_width * 8 - 1) - 1
    result = bytearray()
    for s in samples:
        val = int(max(0.0, min(1.0, s)) * max_val)
        result.extend(struct.pack(fmt, val))
    return bytes(result)

def add(fragment1, fragment2, width):
    """Add two audio fragments."""    
    s1 = _int16_to_float(fragment1, width)
    s2 = _int16_to_float(fragment2, width)
    result = [max(-1.0, min(1.0, a + b)) for a, b in zip(s1, s2)]
    return _float_to_int16(result, width)

def mul(fragment, width, factor):
    """Multiply audio fragment by factor."""
    samples = _int16_to_float(fragment, width)
    result = [max(-1.0, min(1.0, s * factor)) for s in samples]
    return _float_to_int16(result, width)

def rms(fragment, width):
    """Return RMS value of audio fragment."""
    samples = _int16_to_float(fragment, width)
    if not samples:
        return 0
    return int(math.sqrt(sum(s * s for s in samples) / len(samples)) * (2 ** (width * 8 - 1)))

def max(fragment, width):
    """Return maximum absolute value in audio fragment."""
    samples = _int16_to_float(fragment, width)
    if not samples:
        return 0
    return int(max(abs(s) for s in samples) * (2 ** (width * 8 - 1)))

def maxpp(fragment, width):
    """Return peak-to-peak value."""
    samples = _int16_to_float(fragment, width)
    if not samples:
        return 0
    return int((max(samples) - min(samples)) * (2 ** (width * 8 - 1)))

def avg(fragment, width):
    """Return average value of audio fragment."""
    samples = _int16_to_float(fragment, width)
    if not samples:
        return 0
    return int((sum(samples) / len(samples)) * (2 ** (width * 8 - 1)))

def minmax(fragment, width):
    """Return (min, max) of audio fragment."""
    samples = _int16_to_float(fragment, width)
    if not samples:
        return (0, 0)
    m = 2 ** (width * 8 - 1)
    return (int(min(samples) * m), int(max(samples) * m))

def tomono(fragment, width, lfactor, rfactor):
    """Convert stereo to mono."""
    bytes_per_sample = width
    total_samples = len(fragment) // (2 * bytes_per_sample)
    result = bytearray()
    fmt = {1: "b", 2: "h", 4: "i"}[width]
    for i in range(total_samples):
        offset = i * 2 * bytes_per_sample
        left = struct.unpack_from(fmt, fragment, offset)[0]
        right = struct.unpack_from(fmt, fragment, offset + bytes_per_sample)[0]
        mono = int(left * lfactor + right * rfactor)
        result.extend(struct.pack(fmt, mono))
    return bytes(result)

def tostereo(fragment, width, lfactor, rfactor):
    """Convert mono to stereo."""
    bytes_per_sample = width
    total_samples = len(fragment) // bytes_per_sample
    result = bytearray()
    fmt = {1: "b", 2: "h", 4: "i"}[width]
    for i in range(total_samples):
        val = struct.unpack_from(fmt, fragment, i * bytes_per_sample)[0]
        left = int(val * lfactor)
        right = int(val * rfactor)
        result.extend(struct.pack(fmt, left))
        result.extend(struct.pack(fmt, right))
    return bytes(result)

def reverse(fragment, width):
    """Reverse audio fragment."""
    bytes_per_sample = width
    samples = [fragment[i:i + bytes_per_sample] for i in range(0, len(fragment), bytes_per_sample)]
    samples.reverse()
    return b"".join(samples)

def bias(fragment, width, bias_val):
    """Add bias to audio fragment."""
    samples = list(fragment)
    result = bytearray()
    # Simple bias for 8/16-bit
    for i in range(0, len(samples), width):
        val = struct.unpack_from({1: "b", 2: "h", 4: "i"}[width], fragment, i)[0]
        val += bias_val
        result.extend(struct.pack({1: "b", 2: "h", 4: "i"}[width], val))
    return bytes(result)

def lin2lin(fragment, width, newwidth):
    """Convert linear samples between widths."""
    if width == newwidth:
        return fragment
    samples = _int16_to_float(fragment, width)
    return _float_to_int16(samples, newwidth)

def ratecv(fragment, width, nchannels, inrate, outrate, state=None):
    """Simple rate conversion (nearest-neighbor)."""
    if inrate == outrate:
        return (fragment, state)
    factor = inrate / outrate
    bytes_per_frame = width * nchannels
    in_frames = len(fragment) // bytes_per_frame
    out_frames = int(in_frames / factor)
    result = bytearray()
    for i in range(out_frames):
        src_idx = int(i * factor)
        offset = src_idx * bytes_per_frame
        end = min(offset + bytes_per_frame, len(fragment))
        result.extend(fragment[offset:end])
    return (bytes(result), state)

def ulaw2lin(fragment, width):
    raise NotImplementedError(_error_msg)

def lin2ulaw(fragment, width):
    raise NotImplementedError(_error_msg)

def alaw2lin(fragment, width):
    raise NotImplementedError(_error_msg)

def lin2alaw(fragment, width):
    raise NotImplementedError(_error_msg)

def findfit(fragment, reference):
    raise NotImplementedError(_error_msg)

def findfactor(fragment, reference):
    raise NotImplementedError(_error_msg)

def getsample(fragment, width, index):
    """Get a single sample value."""
    fmt = {1: "b", 2: "h", 4: "i"}[width]
    offset = index * width
    return struct.unpack_from(fmt, fragment, offset)[0]

def findmax(fragment, length):
    raise NotImplementedError(_error_msg)

def cross(fragment, width):
    raise NotImplementedError(_error_msg)

def getsample(fragment, width, index):
    fmt = {1: "b", 2: "h", 4: "i"}[width]
    return struct.unpack_from(fmt, fragment, index * width)[0]

def adpcm2lin(adpcmfragment, width, state):
    raise NotImplementedError(_error_msg)

def lin2adpcm(fragment, width, state):
    raise NotImplementedError(_error_msg)
