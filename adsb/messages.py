from dataclasses import dataclass
from .decoder import ADSBPacket

import numpy as np
import math

def bits_to_int(bits: np.ndarray) -> int:
        value = 0

        for bit in bits:
            value = (value << 1) | int(bit)

        return value

def decode_message(packet: ADSBPacket):
    if packet.downlink_format == 0:
        return decode_df0(packet)

    if packet.downlink_format != 17:
        return None

    type_code = bits_to_int(
        packet.bits[32:37]
    )

    if type_code == 19:
        return decode_velocity(packet)

    if 9 <= type_code <= 18:
        return decode_airborne_position(packet)

    return None


@dataclass
class ModeSShortAirAir:
    icao_address: int
    altitude_ft: int | None

    def __str__(self) -> str:
        altitude = (
            f"{self.altitude_ft} ft"
            if self.altitude_ft is not None
            else "unavailable"
        )

        return "\n".join([
            "Mode S Short Air-Air Surveillance",
            f"  ICAO address:  {self.icao_address:06X}",
            f"  Altitude:      {altitude}",
        ])

def decode_df0(
    packet: ADSBPacket,
) -> ModeSShortAirAir:

    if packet.downlink_format != 0:
        raise ValueError("Expected DF0")

    return ModeSShortAirAir(
        icao_address=packet.crc_remainder,
        altitude_ft=None,
    )

@dataclass
class ADSBVelocity:
    subtype: int

    east_velocity_knots: float
    north_velocity_knots: float

    ground_speed_knots: float
    ground_track_degrees: float

    vertical_rate_fpm: int
    vertical_rate_source: str

    geo_minus_baro_feet: int | None

    def __str__(self) -> str:
        lines = [
            "Airborne Velocity",
            f"  Subtype:        {self.subtype}",
            f"  Ground speed:   {self.ground_speed_knots:.1f} kt",
            f"  Ground track:   {self.ground_track_degrees:.1f}°",
            f"  East velocity:  {self.east_velocity_knots:+.0f} kt",
            f"  North velocity: {self.north_velocity_knots:+.0f} kt",
            (
                f"  Vertical rate:  {self.vertical_rate_fpm:+d} ft/min "
                f"({self.vertical_rate_source})"
            ),
        ]

        if self.geo_minus_baro_feet is not None:
            lines.append(
                f"  GNSS - baro:    {self.geo_minus_baro_feet:+d} ft"
            )

        return "\n".join(lines)

def decode_velocity(packet: ADSBPacket) -> ADSBVelocity:
    if packet.downlink_format != 17:
        raise ValueError("Velocity decoding requires DF17")

    bits = packet.bits

    # ADS-B ME field begins at bit 32.
    type_code = bits_to_int(bits[32:37])

    if type_code != 19:
        raise ValueError(
            f"Expected TC19 velocity message, got TC{type_code}"
        )

    subtype = bits_to_int(bits[37:40])

    if subtype not in (1, 2):
        raise NotImplementedError(
            f"TC19 subtype {subtype} not supported yet"
        )

    # East/west velocity
    ew_direction = bits[45]
    ew_raw = bits_to_int(bits[46:56])

    # North/south velocity
    ns_direction = bits[56]
    ns_raw = bits_to_int(bits[57:67])

    # Raw zero means "no information".
    if ew_raw == 0 or ns_raw == 0:
        raise ValueError("Velocity component unavailable")

    ew_velocity = ew_raw - 1
    ns_velocity = ns_raw - 1

    # Subtype 2 has 4-knot resolution.
    scale = 1 if subtype == 1 else 4

    ew_velocity *= scale
    ns_velocity *= scale

    # 0 = east/north, 1 = west/south
    if ew_direction:
        ew_velocity = -ew_velocity

    if ns_direction:
        ns_velocity = -ns_velocity

    ground_speed = math.hypot(
        ew_velocity,
        ns_velocity,
    )

    ground_track = math.degrees(
        math.atan2(
            ew_velocity,
            ns_velocity,
        )
    ) % 360.0

    # Vertical rate
    vr_source = (
        "barometric"
        if bits[68] == 1
        else "GNSS"
    )

    vr_sign = bits[69]
    vr_raw = bits_to_int(bits[70:79])

    if vr_raw == 0:
        vertical_rate = 0
    else:
        vertical_rate = (vr_raw - 1) * 64

        if vr_sign:
            vertical_rate = -vertical_rate

    # GNSS altitude minus barometric altitude
    diff_sign = bits[80]
    diff_raw = bits_to_int(bits[81:88])

    if diff_raw == 0:
        geo_minus_baro = None
    else:
        geo_minus_baro = (diff_raw - 1) * 25

        if diff_sign:
            geo_minus_baro = -geo_minus_baro

    return ADSBVelocity(
        subtype=subtype,
        east_velocity_knots=ew_velocity,
        north_velocity_knots=ns_velocity,
        ground_speed_knots=ground_speed,
        ground_track_degrees=ground_track,
        vertical_rate_fpm=vertical_rate,
        vertical_rate_source=vr_source,
        geo_minus_baro_feet=geo_minus_baro,
    )

@dataclass
class ADSBAirbornePosition:
    type_code: int
    altitude_ft: int | None

    odd: bool
    time_flag: int

    cpr_latitude: int
    cpr_longitude: int

    def __str__(self) -> str:
        frame_type = "odd" if self.odd else "even"

        altitude = (
            f"{self.altitude_ft} ft"
            if self.altitude_ft is not None
            else "unavailable"
        )

        return "\n".join([
            "Airborne Position",
            f"  Type code:      TC{self.type_code}",
            f"  Altitude:       {altitude}",
            f"  CPR format:      {frame_type}",
            f"  CPR latitude:   {self.cpr_latitude}",
            f"  CPR longitude:  {self.cpr_longitude}",
            f"  Time flag:      {self.time_flag}",
        ])

def decode_airborne_position(
    packet: ADSBPacket,
) -> ADSBAirbornePosition:

    if packet.downlink_format != 17:
        raise ValueError(
            "Airborne position decoding requires DF17"
        )

    bits = packet.bits

    type_code = bits_to_int(bits[32:37])

    if not 9 <= type_code <= 18:
        raise ValueError(
            f"Expected airborne-position message, "
            f"got TC{type_code}"
        )

    # 12-bit altitude field: message bits 41-52
    altitude_bits = bits[40:52]

    # Q bit is bit 48 in ADS-B's 1-based numbering,
    # which is index 47 in our zero-based array.
    q_bit = int(bits[47])

    altitude_ft = None

    if q_bit == 1:
        # Remove the Q bit to form the 11-bit N value.
        n_bits = np.concatenate([
            altitude_bits[:7],
            altitude_bits[8:],
        ])

        n = bits_to_int(n_bits)

        altitude_ft = n * 25 - 1000

    time_flag = int(bits[52])
    odd = bool(bits[53])

    cpr_latitude = bits_to_int(
        bits[54:71]
    )

    cpr_longitude = bits_to_int(
        bits[71:88]
    )

    return ADSBAirbornePosition(
        type_code=type_code,
        altitude_ft=altitude_ft,
        odd=odd,
        time_flag=time_flag,
        cpr_latitude=cpr_latitude,
        cpr_longitude=cpr_longitude,
    )