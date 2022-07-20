def get_orbit_angle(orbit: int, orbit_index: int, data: dict) -> float:
    nodes_in_orbit = data['constants']['skillsPerOrbit']

    if orbit == 2 or orbit == 3:
        orbit_angles = [0, 30, 45, 60, 90, 120, 135, 150, 180, 210, 225, 240, 270, 300, 315, 330]
        return orbit_angles[orbit_index]
    elif orbit == 4:
        orbit_angles = [0, 10, 20, 30, 40, 45, 50, 60, 70, 80, 90, 100, 110, 120, 130, 135, 140, 150, 160, 170, 180, 190, 200, 210, 220, 225, 230, 240, 250, 260, 270, 280, 290, 300, 310, 315, 320, 330, 340, 350]
        return orbit_angles[orbit_index]
    else:
        return 360 / nodes_in_orbit[orbit] * orbit_index
