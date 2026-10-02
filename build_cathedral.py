#!/usr/bin/env python3
"""
3D Model Generator for the Nativity Cathedral of Chisinau (Catedrala Nașterea Domnului din Chișinău)
Designed by architect Abram Melnikov (1830–1836).
Generates:
- cathedral_chisinau.obj + cathedral_chisinau.mtl
- cathedral_chisinau.glb (glTF 2.0 binary)
- cathedral_chisinau.stl (for 3D printing)
- index.html (interactive 3D viewer with Three.js)
"""

import math
import struct
import json
import os
import sys

class MeshBuilder:
    def __init__(self):
        self.vertices = []      # list of (x, y, z)
        self.normals = []       # list of (nx, ny, nz)
        self.uvs = []           # list of (u, v)
        self.materials = {}     # mat_name -> list of faces [((v1, vt1, vn1), (v2, vt2, vn2), (v3, vt3, vn3))]
        self.current_material = "Wall_Cream"

    def set_material(self, mat_name):
        self.current_material = mat_name
        if mat_name not in self.materials:
            self.materials[mat_name] = []

    def add_vertex(self, x, y, z):
        self.vertices.append((float(x), float(y), float(z)))
        return len(self.vertices)  # 1-indexed for OBJ

    def add_normal(self, nx, ny, nz):
        l = math.sqrt(nx*nx + ny*ny + nz*nz)
        if l > 1e-9:
            nx, ny, nz = nx/l, ny/l, nz/l
        else:
            nx, ny, nz = 0.0, 1.0, 0.0
        self.normals.append((float(nx), float(ny), float(nz)))
        return len(self.normals)

    def add_uv(self, u, v):
        self.uvs.append((float(u), float(v)))
        return len(self.uvs)

    def add_triangle(self, v1, v2, v3, vt1=None, vt2=None, vt3=None, vn1=None, vn2=None, vn3=None):
        if vn1 is None:
            # calculate flat normal
            p1 = self.vertices[v1 - 1]
            p2 = self.vertices[v2 - 1]
            p3 = self.vertices[v3 - 1]
            ux, uy, uz = p2[0]-p1[0], p2[1]-p1[1], p2[2]-p1[2]
            vx, vy, vz = p3[0]-p1[0], p3[1]-p1[1], p3[2]-p1[2]
            nx = uy*vz - uz*vy
            ny = uz*vx - ux*vz
            nz = ux*vy - uy*vx
            norm_idx = self.add_normal(nx, ny, nz)
            vn1 = vn2 = vn3 = norm_idx

        if vt1 is None:
            vt1 = self.add_uv(0.0, 0.0)
            vt2 = self.add_uv(1.0, 0.0)
            vt3 = self.add_uv(0.5, 1.0)

        face = ((v1, vt1, vn1), (v2, vt2, vn2), (v3, vt3, vn3))
        if self.current_material not in self.materials:
            self.materials[self.current_material] = []
        self.materials[self.current_material].append(face)

    def add_quad(self, v1, v2, v3, v4, vt1=None, vt2=None, vt3=None, vt4=None, vn1=None, vn2=None, vn3=None, vn4=None):
        # Two triangles: v1, v2, v3 and v1, v3, v4
        if vt1 is None:
            vt1 = self.add_uv(0.0, 0.0)
            vt2 = self.add_uv(1.0, 0.0)
            vt3 = self.add_uv(1.0, 1.0)
            vt4 = self.add_uv(0.0, 1.0)

        self.add_triangle(v1, v2, v3, vt1, vt2, vt3, vn1, vn2, vn3)
        self.add_triangle(v1, v3, v4, vt1, vt3, vt4, vn1, vn3, vn4)

    # Primitive helpers
    def add_box(self, cx, cy, cz, sx, sy, sz, mat=None):
        """Axis aligned box centered at (cx, cy, cz) with dimensions sx, sy, sz"""
        if mat: self.set_material(mat)
        hx, hy, hz = sx/2.0, sy/2.0, sz/2.0
        
        # 8 vertices
        # 0: -hx, -hy, -hz
        # 1: +hx, -hy, -hz
        # 2: +hx, +hy, -hz
        # 3: -hx, +hy, -hz
        # 4: -hx, -hy, +hz
        # 5: +hx, -hy, +hz
        # 6: +hx, +hy, +hz
        # 7: -hx, +hy, +hz
        v = [
            self.add_vertex(cx - hx, cy - hy, cz - hz),
            self.add_vertex(cx + hx, cy - hy, cz - hz),
            self.add_vertex(cx + hx, cy + hy, cz - hz),
            self.add_vertex(cx - hx, cy + hy, cz - hz),
            self.add_vertex(cx - hx, cy - hy, cz + hz),
            self.add_vertex(cx + hx, cy - hy, cz + hz),
            self.add_vertex(cx + hx, cy + hy, cz + hz),
            self.add_vertex(cx - hx, cy + hy, cz + hz)
        ]

        # Normals
        n_front  = self.add_normal(0, 0, 1)
        n_back   = self.add_normal(0, 0, -1)
        n_top    = self.add_normal(0, 1, 0)
        n_bottom = self.add_normal(0, -1, 0)
        n_right  = self.add_normal(1, 0, 0)
        n_left   = self.add_normal(-1, 0, 0)

        # UVs
        t0 = self.add_uv(0, 0)
        t1 = self.add_uv(1, 0)
        t2 = self.add_uv(1, 1)
        t3 = self.add_uv(0, 1)

        # Front (+Z)
        self.add_quad(v[4], v[5], v[6], v[7], t0, t1, t2, t3, n_front, n_front, n_front, n_front)
        # Back (-Z)
        self.add_quad(v[1], v[0], v[3], v[2], t0, t1, t2, t3, n_back, n_back, n_back, n_back)
        # Top (+Y)
        self.add_quad(v[7], v[6], v[2], v[3], t0, t1, t2, t3, n_top, n_top, n_top, n_top)
        # Bottom (-Y)
        self.add_quad(v[0], v[1], v[5], v[4], t0, t1, t2, t3, n_bottom, n_bottom, n_bottom, n_bottom)
        # Right (+X)
        self.add_quad(v[5], v[1], v[2], v[6], t0, t1, t2, t3, n_right, n_right, n_right, n_right)
        # Left (-X)
        self.add_quad(v[0], v[4], v[7], v[3], t0, t1, t2, t3, n_left, n_left, n_left, n_left)

    def add_cylinder(self, cx, y_base, cz, r_bottom, r_top, height, segments=24, mat=None, cap_bottom=True, cap_top=True):
        if mat: self.set_material(mat)
        v_bottom = []
        v_top = []
        n_side = []
        
        y_top = y_base + height
        slant = (r_bottom - r_top) / height if height > 0 else 0

        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)

            vx_b = cx + r_bottom * cos_a
            vz_b = cz + r_bottom * sin_a
            vx_t = cx + r_top * cos_a
            vz_t = cz + r_top * sin_a

            v_bottom.append(self.add_vertex(vx_b, y_base, vz_b))
            v_top.append(self.add_vertex(vx_t, y_top, vz_t))
            n_side.append(self.add_normal(cos_a, slant, sin_a))

        # Side quads
        for i in range(segments):
            next_i = (i + 1) % segments
            u0 = i / segments
            u1 = (i + 1) / segments
            vt0 = self.add_uv(u0, 0)
            vt1 = self.add_uv(u1, 0)
            vt2 = self.add_uv(u1, 1)
            vt3 = self.add_uv(u0, 1)

            self.add_quad(
                v_bottom[i], v_bottom[next_i], v_top[next_i], v_top[i],
                vt0, vt1, vt2, vt3,
                n_side[i], n_side[next_i], n_side[next_i], n_side[i]
            )

        # Caps
        if cap_bottom:
            n_down = self.add_normal(0, -1, 0)
            v_center_b = self.add_vertex(cx, y_base, cz)
            vt_c = self.add_uv(0.5, 0.5)
            for i in range(segments):
                next_i = (i + 1) % segments
                self.add_triangle(v_center_b, v_bottom[next_i], v_bottom[i], vt_c, None, None, n_down, n_down, n_down)

        if cap_top:
            n_up = self.add_normal(0, 1, 0)
            v_center_t = self.add_vertex(cx, y_top, cz)
            vt_c = self.add_uv(0.5, 0.5)
            for i in range(segments):
                next_i = (i + 1) % segments
                self.add_triangle(v_center_t, v_top[i], v_top[next_i], vt_c, None, None, n_up, n_up, n_up)

    def add_dome(self, cx, cy, cz, radius, height, lat_segments=16, lon_segments=32, mat=None):
        """Upper hemisphere dome with smooth normals"""
        if mat: self.set_material(mat)
        grid = []
        norm_grid = []
        uv_grid = []

        for lat in range(lat_segments + 1):
            theta = (math.pi / 2.0) * (lat / lat_segments) # 0 (equator) to pi/2 (apex)
            y = cy + height * math.sin(theta)
            r_lat = radius * math.cos(theta)
            row_v = []
            row_n = []
            row_uv = []

            for lon in range(lon_segments + 1):
                phi = 2.0 * math.pi * (lon / lon_segments)
                x = cx + r_lat * math.cos(phi)
                z = cz + r_lat * math.sin(phi)

                # Normal: spherical vector
                nx = math.cos(theta) * math.cos(phi)
                ny = math.sin(theta)
                nz = math.cos(theta) * math.sin(phi)

                row_v.append(self.add_vertex(x, y, z))
                row_n.append(self.add_normal(nx, ny, nz))
                row_uv.append(self.add_uv(lon / lon_segments, lat / lat_segments))

            grid.append(row_v)
            norm_grid.append(row_n)
            uv_grid.append(row_uv)

        for lat in range(lat_segments):
            for lon in range(lon_segments):
                v1 = grid[lat][lon]
                v2 = grid[lat][lon + 1]
                v3 = grid[lat + 1][lon + 1]
                v4 = grid[lat + 1][lon]

                n1 = norm_grid[lat][lon]
                n2 = norm_grid[lat][lon + 1]
                n3 = norm_grid[lat + 1][lon + 1]
                n4 = norm_grid[lat + 1][lon]

                t1 = uv_grid[lat][lon]
                t2 = uv_grid[lat][lon + 1]
                t3 = uv_grid[lat + 1][lon + 1]
                t4 = uv_grid[lat + 1][lon]

                if lat == lat_segments - 1:
                    # Top apex triangle
                    self.add_triangle(v1, v2, v3, t1, t2, t3, n1, n2, n3)
                else:
                    self.add_quad(v1, v2, v3, v4, t1, t2, t3, t4, n1, n2, n3, n4)

    def add_doric_column(self, cx, y_base, cz, height=9.0, base_radius=0.55, top_radius=0.46, mat="Stone_White"):
        """Classical Doric column with stepped base, fluted shaft, echinus, and abacus capital"""
        self.set_material(mat)
        # 1. Base plinth (square base block)
        plinth_size = base_radius * 2.5
        plinth_h = height * 0.04
        self.add_box(cx, y_base + plinth_h/2.0, cz, plinth_size, plinth_h, plinth_size, mat)

        # 2. Torus molding (rounded base ring)
        torus_h = height * 0.03
        self.add_cylinder(cx, y_base + plinth_h, cz, base_radius * 1.15, base_radius, torus_h, segments=20, mat=mat)

        # 3. Column shaft with classical Doric entasis taper
        shaft_base_y = y_base + plinth_h + torus_h
        shaft_h = height * 0.84
        self.add_cylinder(cx, shaft_base_y, cz, base_radius, top_radius, shaft_h, segments=20, mat=mat)

        # 4. Capital: Echinus (flaring neck molding)
        echinus_y = shaft_base_y + shaft_h
        echinus_h = height * 0.045
        self.add_cylinder(cx, echinus_y, cz, top_radius, top_radius * 1.35, echinus_h, segments=20, mat=mat)

        # 5. Capital: Abacus (square slab)
        abacus_y = echinus_y + echinus_h
        abacus_h = height * 0.045
        abacus_size = top_radius * 2.8
        self.add_box(cx, abacus_y + abacus_h/2.0, cz, abacus_size, abacus_h, abacus_size, mat)

    def add_pediment(self, cx, y_base, cz, width, rise, depth, direction='Z', sign=1, mat="Stone_White"):
        """Classical triangular pediment with recessed tympanum and sloping cornices"""
        self.set_material(mat)
        hw = width / 2.0
        y_peak = y_base + rise

        # Compute vertices for front triangular face and rear triangular face
        if direction == 'Z':
            z_front = cz + sign * depth / 2.0
            z_back  = cz - sign * depth / 2.0

            v1_f = self.add_vertex(cx - hw, y_base, z_front)
            v2_f = self.add_vertex(cx + hw, y_base, z_front)
            v3_f = self.add_vertex(cx, y_peak, z_front)

            v1_b = self.add_vertex(cx - hw, y_base, z_back)
            v2_b = self.add_vertex(cx + hw, y_base, z_back)
            v3_b = self.add_vertex(cx, y_peak, z_back)

            n_front = self.add_normal(0, 0, sign)
            n_back  = self.add_normal(0, 0, -sign)

            if sign > 0:
                self.add_triangle(v1_f, v2_f, v3_f, vn1=n_front, vn2=n_front, vn3=n_front)
                self.add_triangle(v2_b, v1_b, v3_b, vn1=n_back, vn2=n_back, vn3=n_back)
            else:
                self.add_triangle(v2_f, v1_f, v3_f, vn1=n_front, vn2=n_front, vn3=n_front)
                self.add_triangle(v1_b, v2_b, v3_b, vn1=n_back, vn2=n_back, vn3=n_back)

            # Left slope
            n_left = self.add_normal(-rise, hw, 0)
            self.add_quad(v1_b, v1_f, v3_f, v3_b, vn1=n_left, vn2=n_left, vn3=n_left, vn4=n_left)

            # Right slope
            n_right = self.add_normal(rise, hw, 0)
            self.add_quad(v2_f, v2_b, v3_b, v3_f, vn1=n_right, vn2=n_right, vn3=n_right, vn4=n_right)

            # Bottom face
            n_bottom = self.add_normal(0, -1, 0)
            self.add_quad(v1_b, v2_b, v2_f, v1_f, vn1=n_bottom, vn2=n_bottom, vn3=n_bottom, vn4=n_bottom)

        else: # direction == 'X'
            x_front = cx + sign * depth / 2.0
            x_back  = cx - sign * depth / 2.0

            v1_f = self.add_vertex(x_front, y_base, cz - hw)
            v2_f = self.add_vertex(x_front, y_base, cz + hw)
            v3_f = self.add_vertex(x_front, y_peak, cz)

            v1_b = self.add_vertex(x_back, y_base, cz - hw)
            v2_b = self.add_vertex(x_back, y_base, cz + hw)
            v3_b = self.add_vertex(x_back, y_peak, cz)

            n_front = self.add_normal(sign, 0, 0)
            n_back  = self.add_normal(-sign, 0, 0)

            if sign > 0:
                self.add_triangle(v1_f, v2_f, v3_f, vn1=n_front, vn2=n_front, vn3=n_front)
                self.add_triangle(v2_b, v1_b, v3_b, vn1=n_back, vn2=n_back, vn3=n_back)
            else:
                self.add_triangle(v2_f, v1_f, v3_f, vn1=n_front, vn2=n_front, vn3=n_front)
                self.add_triangle(v1_b, v2_b, v3_b, vn1=n_back, vn2=n_back, vn3=n_back)

            # Slopes
            n_left = self.add_normal(0, hw, -rise)
            self.add_quad(v1_b, v1_f, v3_f, v3_b, vn1=n_left, vn2=n_left, vn3=n_left, vn4=n_left)

            n_right = self.add_normal(0, hw, rise)
            self.add_quad(v2_f, v2_b, v3_b, v3_f, vn1=n_right, vn2=n_right, vn3=n_right, vn4=n_right)

            n_bottom = self.add_normal(0, -1, 0)
            self.add_quad(v1_b, v2_b, v2_f, v1_f, vn1=n_bottom, vn2=n_bottom, vn3=n_bottom, vn4=n_bottom)

    def add_arch(self, cx, y_spring, cz, inner_r, outer_r, depth, height_straight=0, segments=12, axis='Z', mat="Stone_White"):
        """Classical semicircular arch with depth"""
        self.set_material(mat)
        hd = depth / 2.0
        
        # Straight jambs if height_straight > 0
        if height_straight > 0:
            if axis == 'Z':
                # Left jamb
                self.add_box(cx - (inner_r + outer_r)/2.0, y_spring - height_straight/2.0, cz, outer_r - inner_r, height_straight, depth, mat)
                # Right jamb
                self.add_box(cx + (inner_r + outer_r)/2.0, y_spring - height_straight/2.0, cz, outer_r - inner_r, height_straight, depth, mat)
            else:
                # Left jamb in Z
                self.add_box(cx, y_spring - height_straight/2.0, cz - (inner_r + outer_r)/2.0, depth, height_straight, outer_r - inner_r, mat)
                # Right jamb in Z
                self.add_box(cx, y_spring - height_straight/2.0, cz + (inner_r + outer_r)/2.0, depth, height_straight, outer_r - inner_r, mat)

        # Arch ring
        angles = [math.pi * i / segments for i in range(segments + 1)] # 0 to pi (right to left)
        pts_inner = []
        pts_outer = []

        for a in angles:
            cos_a = math.cos(a)
            sin_a = math.sin(a)
            pts_inner.append((inner_r * cos_a, inner_r * sin_a))
            pts_outer.append((outer_r * cos_a, outer_r * sin_a))

        for i in range(segments):
            p_in1, p_in2 = pts_inner[i], pts_inner[i+1]
            p_out1, p_out2 = pts_outer[i], pts_outer[i+1]

            if axis == 'Z':
                # Front face (+Z)
                v_in1_f  = self.add_vertex(cx + p_in1[0], y_spring + p_in1[1], cz + hd)
                v_in2_f  = self.add_vertex(cx + p_in2[0], y_spring + p_in2[1], cz + hd)
                v_out1_f = self.add_vertex(cx + p_out1[0], y_spring + p_out1[1], cz + hd)
                v_out2_f = self.add_vertex(cx + p_out2[0], y_spring + p_out2[1], cz + hd)

                # Back face (-Z)
                v_in1_b  = self.add_vertex(cx + p_in1[0], y_spring + p_in1[1], cz - hd)
                v_in2_b  = self.add_vertex(cx + p_in2[0], y_spring + p_in2[1], cz - hd)
                v_out1_b = self.add_vertex(cx + p_out1[0], y_spring + p_out1[1], cz - hd)
                v_out2_b = self.add_vertex(cx + p_out2[0], y_spring + p_out2[1], cz - hd)

                n_f = self.add_normal(0, 0, 1)
                n_b = self.add_normal(0, 0, -1)

                self.add_quad(v_in1_f, v_out1_f, v_out2_f, v_in2_f, vn1=n_f, vn2=n_f, vn3=n_f, vn4=n_f)
                self.add_quad(v_in2_b, v_out2_b, v_out1_b, v_in1_b, vn1=n_b, vn2=n_b, vn3=n_b, vn4=n_b)

                # Intrados (inner soffit)
                n_in1 = self.add_normal(math.cos(angles[i]), math.sin(angles[i]), 0)
                n_in2 = self.add_normal(math.cos(angles[i+1]), math.sin(angles[i+1]), 0)
                self.add_quad(v_in1_b, v_in1_f, v_in2_f, v_in2_b, vn1=n_in1, vn2=n_in1, vn3=n_in2, vn4=n_in2)

                # Extrados (outer curve)
                n_out1 = self.add_normal(-math.cos(angles[i]), -math.sin(angles[i]), 0)
                n_out2 = self.add_normal(-math.cos(angles[i+1]), -math.sin(angles[i+1]), 0)
                self.add_quad(v_out1_f, v_out1_b, v_out2_b, v_out2_f, vn1=n_out1, vn2=n_out1, vn3=n_out2, vn4=n_out2)
            else:
                # Along X axis
                v_in1_f  = self.add_vertex(cx + hd, y_spring + p_in1[1], cz + p_in1[0])
                v_in2_f  = self.add_vertex(cx + hd, y_spring + p_in2[1], cz + p_in2[0])
                v_out1_f = self.add_vertex(cx + hd, y_spring + p_out1[1], cz + p_out1[0])
                v_out2_f = self.add_vertex(cx + hd, y_spring + p_out2[1], cz + p_out2[0])

                v_in1_b  = self.add_vertex(cx - hd, y_spring + p_in1[1], cz + p_in1[0])
                v_in2_b  = self.add_vertex(cx - hd, y_spring + p_in2[1], cz + p_in2[0])
                v_out1_b = self.add_vertex(cx - hd, y_spring + p_out1[1], cz + p_out1[0])
                v_out2_b = self.add_vertex(cx - hd, y_spring + p_out2[1], cz + p_out2[0])

                n_f = self.add_normal(1, 0, 0)
                n_b = self.add_normal(-1, 0, 0)

                self.add_quad(v_in1_f, v_out1_f, v_out2_f, v_in2_f, vn1=n_f, vn2=n_f, vn3=n_f, vn4=n_f)
                self.add_quad(v_in2_b, v_out2_b, v_out1_b, v_in1_b, vn1=n_b, vn2=n_b, vn3=n_b, vn4=n_b)

                n_in1 = self.add_normal(0, math.sin(angles[i]), math.cos(angles[i]))
                n_in2 = self.add_normal(0, math.sin(angles[i+1]), math.cos(angles[i+1]))
                self.add_quad(v_in1_b, v_in1_f, v_in2_f, v_in2_b, vn1=n_in1, vn2=n_in1, vn3=n_in2, vn4=n_in2)

                n_out1 = self.add_normal(0, -math.sin(angles[i]), -math.cos(angles[i]))
                n_out2 = self.add_normal(0, -math.sin(angles[i+1]), -math.cos(angles[i+1]))
                self.add_quad(v_out1_f, v_out1_b, v_out2_b, v_out2_f, vn1=n_out1, vn2=n_out1, vn3=n_out2, vn4=n_out2)

    def add_orthodox_cross(self, cx, y_base, cz, height=3.5, mat="Gold_Cross"):
        """Detailed Orthodox three-bar cross with golden finials"""
        self.set_material(mat)
        beam_w = height * 0.08
        beam_d = height * 0.08

        # 1. Main vertical post
        self.add_box(cx, y_base + height/2.0, cz, beam_w, height, beam_d, mat)

        # 2. Main horizontal crossbeam
        main_bar_w = height * 0.65
        main_bar_y = y_base + height * 0.68
        self.add_box(cx, main_bar_y, cz, main_bar_w, beam_w, beam_d, mat)

        # Trefoil finials on main bar ends
        finial_r = beam_w * 0.8
        self.add_cylinder(cx - main_bar_w/2.0, main_bar_y - finial_r, cz, finial_r, finial_r, finial_r*2, segments=8, mat=mat)
        self.add_cylinder(cx + main_bar_w/2.0, main_bar_y - finial_r, cz, finial_r, finial_r, finial_r*2, segments=8, mat=mat)

        # 3. Upper inscription bar (Titulus)
        top_bar_w = height * 0.32
        top_bar_y = y_base + height * 0.86
        self.add_box(cx, top_bar_y, cz, top_bar_w, beam_w * 0.85, beam_d, mat)

        # 4. Lower slanted footrest bar (Suppedaneum) - tilted ~15 degrees
        foot_bar_w = height * 0.38
        foot_bar_y = y_base + height * 0.28
        # We can construct the tilted bar with rotated box vertices
        tilt_ang = math.radians(16.0)
        cos_t, sin_t = math.cos(tilt_ang), math.sin(tilt_ang)
        hw, hh, hd = foot_bar_w/2.0, (beam_w * 0.85)/2.0, beam_d/2.0

        # Local corner coords: (+/- hw, +/- hh)
        def rot(lx, ly):
            return cx + lx*cos_t - ly*sin_t, foot_bar_y + lx*sin_t + ly*cos_t

        c0 = rot(-hw, -hh)
        c1 = rot(+hw, -hh)
        c2 = rot(+hw, +hh)
        c3 = rot(-hw, +hh)

        v_f = [
            self.add_vertex(c0[0], c0[1], cz + hd),
            self.add_vertex(c1[0], c1[1], cz + hd),
            self.add_vertex(c2[0], c2[1], cz + hd),
            self.add_vertex(c3[0], c3[1], cz + hd),
        ]
        v_b = [
            self.add_vertex(c0[0], c0[1], cz - hd),
            self.add_vertex(c1[0], c1[1], cz - hd),
            self.add_vertex(c2[0], c2[1], cz - hd),
            self.add_vertex(c3[0], c3[1], cz - hd),
        ]

        nf = self.add_normal(0, 0, 1)
        nb = self.add_normal(0, 0, -1)
        self.add_quad(v_f[0], v_f[1], v_f[2], v_f[3], vn1=nf, vn2=nf, vn3=nf, vn4=nf)
        self.add_quad(v_b[1], v_b[0], v_b[3], v_b[2], vn1=nb, vn2=nb, vn3=nb, vn4=nb)

        # Sides of tilted footrest
        n_bot = self.add_normal(sin_t, -cos_t, 0)
        self.add_quad(v_b[0], v_b[1], v_f[1], v_f[0], vn1=n_bot, vn2=n_bot, vn3=n_bot, vn4=n_bot)
        n_top = self.add_normal(-sin_t, cos_t, 0)
        self.add_quad(v_b[3], v_f[3], v_f[2], v_b[2], vn1=n_top, vn2=n_top, vn3=n_top, vn4=n_top)
        n_rt = self.add_normal(cos_t, sin_t, 0)
        self.add_quad(v_b[1], v_b[2], v_f[2], v_f[1], vn1=n_rt, vn2=n_rt, vn3=n_rt, vn4=n_rt)
        n_lt = self.add_normal(-cos_t, -sin_t, 0)
        self.add_quad(v_b[0], v_f[0], v_f[3], v_b[3], vn1=n_lt, vn2=n_lt, vn3=n_lt, vn4=n_lt)

    def add_stairs(self, cx, y_base, cz, width, run, total_height, num_steps=6, direction='Z', sign=1, mat="Stylobate_Granite"):
        """Flight of classical stone steps leading up to portico"""
        self.set_material(mat)
        step_h = total_height / num_steps
        step_d = run / num_steps

        for i in range(num_steps):
            cur_y = y_base + i * step_h
            cur_run = run - i * step_d
            if direction == 'Z':
                cur_z = cz + sign * (i * step_d + cur_run/2.0)
                self.add_box(cx, cur_y + step_h/2.0, cur_z, width, step_h, cur_run, mat)
            else:
                cur_x = cx + sign * (i * step_d + cur_run/2.0)
                self.add_box(cur_x, cur_y + step_h/2.0, cz, cur_run, step_h, width, mat)


def build_cathedral_ensemble():
    mesh = MeshBuilder()

    print("Building Nativity Cathedral of Chisinau...")

    # =========================================================================
    # 1. PARK PLAZA & ENVIRONMENT BASE
    # =========================================================================
    mesh.add_box(0, -0.2, 16.0, 76.0, 0.4, 110.0, "Plaza_Paving")
    
    # Manicured lawn gardens around cathedral
    mesh.add_box(-26.0, 0.05, 0.0, 16.0, 0.1, 40.0, "Park_Lawn")
    mesh.add_box(+26.0, 0.05, 0.0, 16.0, 0.1, 40.0, "Park_Lawn")
    mesh.add_box(-24.0, 0.05, 48.0, 14.0, 0.1, 30.0, "Park_Lawn")
    mesh.add_box(+24.0, 0.05, 48.0, 14.0, 0.1, 30.0, "Park_Lawn")

    # =========================================================================
    # 2. CATHEDRAL PODIUM / STYLOBATE
    # =========================================================================
    # Main stylobate under core cathedral
    stylobate_h = 0.9
    mesh.add_box(0, stylobate_h/2.0, 0, 28.4, stylobate_h, 28.4, "Stylobate_Granite")

    # Stylobate extensions under the 4 porticos
    portico_w = 16.0
    portico_d = 5.6
    mesh.add_box(0, stylobate_h/2.0, +(14.2 + portico_d/2.0), portico_w, stylobate_h, portico_d, "Stylobate_Granite")
    mesh.add_box(0, stylobate_h/2.0, -(14.2 + portico_d/2.0), portico_w, stylobate_h, portico_d, "Stylobate_Granite")
    mesh.add_box(+(14.2 + portico_d/2.0), stylobate_h/2.0, 0, portico_d, stylobate_h, portico_w, "Stylobate_Granite")
    mesh.add_box(-(14.2 + portico_d/2.0), stylobate_h/2.0, 0, portico_d, stylobate_h, portico_w, "Stylobate_Granite")

    # Grand stone steps on all 4 cardinal approaches (6 steps each)
    stairs_run = 3.6
    mesh.add_stairs(0, 0.0, +(14.2 + portico_d), portico_w + 1.2, stairs_run, stylobate_h, num_steps=6, direction='Z', sign=1)
    mesh.add_stairs(0, 0.0, -(14.2 + portico_d), portico_w + 1.2, stairs_run, stylobate_h, num_steps=6, direction='Z', sign=-1)
    mesh.add_stairs(+(14.2 + portico_d), 0.0, 0, portico_w + 1.2, stairs_run, stylobate_h, num_steps=6, direction='X', sign=1)
    mesh.add_stairs(-(14.2 + portico_d), 0.0, 0, portico_w + 1.2, stairs_run, stylobate_h, num_steps=6, direction='X', sign=-1)

    # =========================================================================
    # 3. CATHEDRAL MAIN BODY (NAOS)
    # =========================================================================
    body_y_base = stylobate_h
    body_h = 12.0
    body_w = 27.0
    body_y_mid = body_y_base + body_h / 2.0

    # Base stone plinth molding around main walls
    mesh.add_box(0, body_y_base + 0.45, 0, body_w + 0.3, 0.9, body_w + 0.3, "Stone_White")

    # Main walls (Cream stucco)
    mesh.add_box(0, body_y_mid, 0, body_w, body_h, body_w, "Wall_Cream")

    # Corner rusticated pilasters / quoins (4 corners)
    corner_size = 5.2
    corner_offset = body_w/2.0 - corner_size/2.0
    for sx in (-1, 1):
        for sz in (-1, 1):
            cx = sx * corner_offset
            cz = sz * corner_offset
            # Corner pilaster projection
            mesh.add_box(cx, body_y_mid, cz, corner_size + 0.25, body_h, corner_size + 0.25, "Stone_White")

    # Windows on exterior wall corners between porticos & corner pilasters
    def add_cathedral_window(cx, cy, cz, axis='Z', sign=1):
        win_w, win_h, win_d = 1.3, 3.2, 0.25
        # Window frame
        if axis == 'Z':
            mesh.add_box(cx, cy, cz + sign*0.08, win_w + 0.3, win_h + 0.3, win_d, "Stone_White")
            # Arched lintel on top of window
            mesh.add_arch(cx, cy + win_h/2.0, cz + sign*0.08, win_w/2.0, win_w/2.0 + 0.15, win_d, segments=10, axis='Z', mat="Stone_White")
            # Dark glass pane
            mesh.add_box(cx, cy, cz + sign*0.04, win_w, win_h, 0.1, "Window_Glass")
        else:
            mesh.add_box(cx + sign*0.08, cy, cz, win_d, win_h + 0.3, win_w + 0.3, "Stone_White")
            mesh.add_arch(cx + sign*0.08, cy + win_h/2.0, cz, win_w/2.0, win_w/2.0 + 0.15, win_d, segments=10, axis='X', mat="Stone_White")
            mesh.add_box(cx + sign*0.04, cy, cz, 0.1, win_h, win_w, "Window_Glass")

    # Add exterior windows on facades
    win_y = body_y_base + 6.0
    for sx in (-10.4, 10.4):
        add_cathedral_window(sx, win_y, +13.52, axis='Z', sign=1)
        add_cathedral_window(sx, win_y, -13.52, axis='Z', sign=-1)
    for sz in (-10.4, 10.4):
        add_cathedral_window(+13.52, win_y, sz, axis='X', sign=1)
        add_cathedral_window(-13.52, win_y, sz, axis='X', sign=-1)

    # Monumental wooden double entrance doors centered behind each portico
    door_w, door_h, door_d = 2.4, 4.4, 0.3
    door_y = body_y_base + door_h/2.0
    # South Door (Main entrance)
    mesh.add_box(0, door_y, +13.55, door_w + 0.5, door_h + 0.5, door_d, "Stone_White")
    mesh.add_box(0, door_y, +13.57, door_w, door_h, 0.12, "Wood_Door")
    # North Door
    mesh.add_box(0, door_y, -13.55, door_w + 0.5, door_h + 0.5, door_d, "Stone_White")
    mesh.add_box(0, door_y, -13.57, door_w, door_h, 0.12, "Wood_Door")
    # East Door
    mesh.add_box(+13.55, door_y, 0, door_d, door_h + 0.5, door_w + 0.5, "Stone_White")
    mesh.add_box(+13.57, door_y, 0, 0.12, door_h, door_w, "Wood_Door")
    # West Door
    mesh.add_box(-13.55, door_y, 0, door_d, door_h + 0.5, door_w + 0.5, "Stone_White")
    mesh.add_box(-13.57, door_y, 0, 0.12, door_h, door_w, "Wood_Door")

    # =========================================================================
    # 4. MAIN ENTABLATURE & CORNICE (AROUND MAIN BODY)
    # =========================================================================
    entablature_y = body_y_base + body_h
    # Architrave band
    mesh.add_box(0, entablature_y + 0.3, 0, body_w + 0.5, 0.6, body_w + 0.5, "Stone_White")
    # Frieze band
    mesh.add_box(0, entablature_y + 0.8, 0, body_w + 0.4, 0.4, body_w + 0.4, "Stone_White")
    # Projecting classical cornice
    mesh.add_box(0, entablature_y + 1.2, 0, body_w + 1.4, 0.4, body_w + 1.4, "Stone_White")

    # =========================================================================
    # 5. FOUR MONUMENTAL DORIC PORTICOS (HEXASTYLE - 6 COLUMNS EACH)
    # =========================================================================
    col_spacing = 2.85 # Spans -7.125 to +7.125
    col_h = 9.2
    col_offsets = [-2.5 * col_spacing, -1.5 * col_spacing, -0.5 * col_spacing,
                    0.5 * col_spacing,  1.5 * col_spacing,  2.5 * col_spacing]

    portico_entab_y = body_y_base + col_h
    pediment_rise = 3.2

    # Portico generation helper
    def build_portico(direction, sign):
        # 6 Doric Columns
        dist = 13.5 + 4.6
        if direction == 'Z':
            cz = sign * dist
            for ox in col_offsets:
                mesh.add_doric_column(ox, body_y_base, cz, height=col_h, base_radius=0.52, top_radius=0.44)

            # Portico Entablature Beam across all columns
            beam_d = 2.2
            mesh.add_box(0, portico_entab_y + 0.35, cz, portico_w, 0.7, beam_d, "Stone_White")
            # Frieze with triglyphs
            mesh.add_box(0, portico_entab_y + 0.9, cz, portico_w, 0.4, beam_d - 0.2, "Stone_White")
            for ox in col_offsets:
                mesh.add_box(ox, portico_entab_y + 0.9, cz + sign*(beam_d/2.0 + 0.05), 0.4, 0.38, 0.1, "Stone_White")
            # Horizontal Cornice
            mesh.add_box(0, portico_entab_y + 1.3, cz, portico_w + 0.8, 0.4, beam_d + 0.8, "Stone_White")

            # Triangular Pediment (Fronton)
            mesh.add_pediment(0, portico_entab_y + 1.5, cz, portico_w + 0.8, pediment_rise, depth=beam_d + 0.8, direction='Z', sign=sign, mat="Stone_White")
            # Pediment Tympanum (slightly recessed)
            mesh.add_pediment(0, portico_entab_y + 1.5, cz + sign*0.1, portico_w * 0.94, pediment_rise * 0.92, depth=0.1, direction='Z', sign=sign, mat="Wall_Cream")

            # Portico Coffered Ceiling & Roof connector to main body
            mesh.add_box(0, portico_entab_y + 1.0, sign * (13.5 + 2.3), portico_w, 0.6, 4.6, "Stone_White")
            # Roof slope connecting pediment to cathedral roof
            mesh.add_box(0, portico_entab_y + 2.2, sign * (13.5 + 2.3), portico_w - 0.6, 1.8, 4.6, "Roof_Zinc")

        else: # direction == 'X'
            cx = sign * dist
            for oz in col_offsets:
                mesh.add_doric_column(cx, body_y_base, oz, height=col_h, base_radius=0.52, top_radius=0.44)

            beam_d = 2.2
            mesh.add_box(cx, portico_entab_y + 0.35, 0, beam_d, 0.7, portico_w, "Stone_White")
            mesh.add_box(cx, portico_entab_y + 0.9, 0, beam_d - 0.2, 0.4, portico_w, "Stone_White")
            for oz in col_offsets:
                mesh.add_box(cx + sign*(beam_d/2.0 + 0.05), portico_entab_y + 0.9, oz, 0.1, 0.38, 0.4, "Stone_White")
            mesh.add_box(cx, portico_entab_y + 1.3, 0, beam_d + 0.8, 0.4, portico_w + 0.8, "Stone_White")

            mesh.add_pediment(cx, portico_entab_y + 1.5, 0, portico_w + 0.8, pediment_rise, depth=beam_d + 0.8, direction='X', sign=sign, mat="Stone_White")
            mesh.add_pediment(cx + sign*0.1, portico_entab_y + 1.5, 0, portico_w * 0.94, pediment_rise * 0.92, depth=0.1, direction='X', sign=sign, mat="Wall_Cream")

            mesh.add_box(sign * (13.5 + 2.3), portico_entab_y + 1.0, 0, 4.6, 0.6, portico_w, "Stone_White")
            mesh.add_box(sign * (13.5 + 2.3), portico_entab_y + 2.2, 0, 4.6, 1.8, portico_w - 0.6, "Roof_Zinc")

    # Build all 4 porticos
    build_portico('Z', +1) # South (Main entrance)
    build_portico('Z', -1) # North
    build_portico('X', +1) # East
    build_portico('X', -1) # West

    # =========================================================================
    # 6. CROSS-GABLE ROOF & ATTIC PLINTH
    # =========================================================================
    # Hip / valley metal roof over main body
    mesh.add_box(0, entablature_y + 1.8, 0, 27.2, 1.2, 27.2, "Roof_Zinc")
    mesh.add_box(0, entablature_y + 2.6, 0, 23.0, 1.0, 23.0, "Roof_Zinc")

    # Square attic terrace supporting rotunda drum
    attic_y = entablature_y + 2.8
    attic_w = 17.5
    mesh.add_box(0, attic_y + 0.6, 0, attic_w, 1.2, attic_w, "Stone_White")
    mesh.add_box(0, attic_y + 1.4, 0, attic_w + 0.6, 0.4, attic_w + 0.6, "Stone_White")

    # Stepped circular pedestal
    drum_base_y = attic_y + 1.6
    mesh.add_cylinder(0, drum_base_y, 0, 8.4, 7.8, 0.8, segments=32, mat="Stone_White")

    # =========================================================================
    # 7. CENTRAL DRUM (ROTUNDA / THOLOBATE)
    # =========================================================================
    drum_y = drum_base_y + 0.8
    drum_r = 7.1
    drum_h = 7.6
    # Drum main cylinder (Wall Cream)
    mesh.add_cylinder(0, drum_y, 0, drum_r, drum_r, drum_h, segments=36, mat="Wall_Cream")

    # Drum bottom molding
    mesh.add_cylinder(0, drum_y, 0, drum_r + 0.25, drum_r + 0.25, 0.6, segments=36, mat="Stone_White")

    # 12 Neoclassical arched windows around the drum (every 30 degrees)
    drum_win_w = 1.3
    drum_win_h = 3.6
    drum_win_y = drum_y + 2.0
    for i in range(12):
        angle = 2.0 * math.pi * i / 12.0
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        wx = (drum_r + 0.05) * cos_a
        wz = (drum_r + 0.05) * sin_a

        # Window frame projection
        mesh.add_box(wx, drum_win_y + drum_win_h/2.0, wz, drum_win_w + 0.4, drum_win_h, 0.3, "Stone_White")
        # Arched top molding
        arch_top_y = drum_win_y + drum_win_h
        mesh.add_cylinder(wx, arch_top_y, wz, (drum_win_w + 0.4)/2.0, (drum_win_w + 0.4)/2.0, 0.3, segments=12, mat="Stone_White")
        # Glass inside window
        mesh.add_box(wx * 0.99, drum_win_y + drum_win_h/2.0, wz * 0.99, drum_win_w, drum_win_h + 0.4, 0.15, "Window_Glass")

        # Classical decorative pilaster between windows
        pilaster_ang = angle + (math.pi / 12.0)
        px = (drum_r + 0.12) * math.cos(pilaster_ang)
        pz = (drum_r + 0.12) * math.sin(pilaster_ang)
        mesh.add_box(px, drum_y + drum_h/2.0, pz, 0.7, drum_h * 0.85, 0.3, "Stone_White")

    # Drum upper entablature and projecting cornice
    drum_top_y = drum_y + drum_h
    mesh.add_cylinder(0, drum_top_y, 0, drum_r + 0.35, drum_r + 0.35, 0.6, segments=36, mat="Stone_White")
    mesh.add_cylinder(0, drum_top_y + 0.6, 0, drum_r + 0.75, drum_r + 0.75, 0.4, segments=36, mat="Stone_White")

    # =========================================================================
    # 8. GRAND HEMISPHERICAL DOME
    # =========================================================================
    dome_y = drum_top_y + 1.0
    dome_r = drum_r + 0.3
    dome_h = 6.6
    # Main metal dome
    mesh.add_dome(0, dome_y, 0, radius=dome_r, height=dome_h, lat_segments=16, lon_segments=36, mat="Dome_Metal")

    # 24 Vertical standing-seam ribs along the dome surface (classic Russian Empire style metal dome)
    for i in range(24):
        angle = 2.0 * math.pi * i / 24.0
        # Build rib by segments
        num_rib_seg = 10
        for seg in range(num_rib_seg):
            t1 = seg / num_rib_seg
            t2 = (seg + 1) / num_rib_seg
            th1 = (math.pi / 2.0) * t1
            th2 = (math.pi / 2.0) * t2
            y1 = dome_y + dome_h * math.sin(th1)
            y2 = dome_y + dome_h * math.sin(th2)
            r1 = (dome_r + 0.08) * math.cos(th1)
            r2 = (dome_r + 0.08) * math.cos(th2)

            rx1, rz1 = r1 * math.cos(angle), r1 * math.sin(angle)
            rx2, rz2 = r2 * math.cos(angle), r2 * math.sin(angle)

            # Tiny box rib
            mesh.add_box((rx1+rx2)/2.0, (y1+y2)/2.0, (rz1+rz2)/2.0, 0.16, max(0.2, abs(y2-y1)), 0.16, "Dome_Metal")

    # =========================================================================
    # 9. LANTERN ROTUNDA & ORTHODOX CROSS
    # =========================================================================
    lantern_base_y = dome_y + dome_h - 0.3
    lantern_r = 1.8
    lantern_h = 2.4

    # Lantern plinth
    mesh.add_cylinder(0, lantern_base_y, 0, lantern_r + 0.3, lantern_r + 0.1, 0.5, segments=24, mat="Stone_White")

    # Lantern cylinder with 8 miniature arched windows
    lantern_cyl_y = lantern_base_y + 0.5
    mesh.add_cylinder(0, lantern_cyl_y, 0, lantern_r, lantern_r, lantern_h, segments=24, mat="Stone_White")
    for i in range(8):
        ang = 2.0 * math.pi * i / 8.0
        lx = (lantern_r + 0.04) * math.cos(ang)
        lz = (lantern_r + 0.04) * math.sin(ang)
        mesh.add_box(lx, lantern_cyl_y + lantern_h/2.0, lz, 0.45, 1.4, 0.15, "Window_Glass")

    # Lantern upper cornice
    lantern_cornice_y = lantern_cyl_y + lantern_h
    mesh.add_cylinder(0, lantern_cornice_y, 0, lantern_r + 0.3, lantern_r + 0.3, 0.35, segments=24, mat="Stone_White")

    # Lantern cupola (small dome)
    cupola_h = 1.3
    mesh.add_dome(0, lantern_cornice_y + 0.35, 0, radius=lantern_r + 0.1, height=cupola_h, lat_segments=10, lon_segments=24, mat="Dome_Metal")

    # Golden sphere finial
    sphere_y = lantern_cornice_y + 0.35 + cupola_h + 0.4
    mesh.add_dome(0, sphere_y - 0.4, 0, radius=0.45, height=0.45, lat_segments=8, lon_segments=16, mat="Gold_Cross")
    mesh.add_cylinder(0, sphere_y - 0.4, 0, 0.45, 0.45, 0.1, segments=16, mat="Gold_Cross")

    # Grand golden Orthodox Cross atop cathedral dome
    mesh.add_orthodox_cross(0, sphere_y + 0.2, 0, height=3.6, mat="Gold_Cross")

    # =========================================================================
    # 10. THE ICONIC BELL TOWER (CLOPOTNIȚA)
    # Reconstructed 4-tier Neoclassical Campanile, located ~40m in front
    # =========================================================================
    bt_cz = 42.0 # 42 meters along front entrance axis
    bt_cx = 0.0

    print("Building Bell Tower (Clopotnița)...")
    # Tier 1: Ground level open monumental triumphal arches
    # Plinth
    bt_w1 = 9.2
    bt_h1 = 7.2
    mesh.add_box(bt_cx, stylobate_h/2.0, bt_cz, bt_w1 + 1.2, stylobate_h, bt_w1 + 1.2, "Stylobate_Granite")
    mesh.add_stairs(bt_cx, 0.0, bt_cz + (bt_w1+1.2)/2.0, bt_w1 + 0.6, 2.4, stylobate_h, num_steps=5, direction='Z', sign=1)
    mesh.add_stairs(bt_cx, 0.0, bt_cz - (bt_w1+1.2)/2.0, bt_w1 + 0.6, 2.4, stylobate_h, num_steps=5, direction='Z', sign=-1)
    mesh.add_stairs(bt_cx + (bt_w1+1.2)/2.0, 0.0, bt_cz, bt_w1 + 0.6, 2.4, stylobate_h, num_steps=5, direction='X', sign=1)
    mesh.add_stairs(bt_cx - (bt_w1+1.2)/2.0, 0.0, bt_cz, bt_w1 + 0.6, 2.4, stylobate_h, num_steps=5, direction='X', sign=-1)

    t1_base_y = stylobate_h
    # 4 Corner Piers of Tier 1
    pier_s = 2.4
    pier_offset = bt_w1/2.0 - pier_s/2.0
    for sx in (-1, 1):
        for sz in (-1, 1):
            px = bt_cx + sx * pier_offset
            pz = bt_cz + sz * pier_offset
            mesh.add_box(px, t1_base_y + bt_h1/2.0, pz, pier_s, bt_h1, pier_s, "Wall_Cream")
            # Classical Doric pilaster on pier face
            mesh.add_box(px, t1_base_y + bt_h1/2.0, pz + sz*(pier_s/2.0 + 0.08), pier_s*0.7, bt_h1, 0.15, "Stone_White")
            mesh.add_box(px + sx*(pier_s/2.0 + 0.08), t1_base_y + bt_h1/2.0, pz, 0.15, bt_h1, pier_s*0.7, "Stone_White")

    # Arches connecting piers on 4 sides (quadrifrons triumphal gate)
    arch_span = bt_w1 - 2.0 * pier_s
    arch_r = arch_span / 2.0
    arch_spring_y = t1_base_y + 4.2
    # Z-axis arches (North and South)
    mesh.add_arch(bt_cx, arch_spring_y, bt_cz + bt_w1/2.0 - 0.2, arch_r, arch_r + 0.45, 0.4, segments=12, axis='Z', mat="Stone_White")
    mesh.add_arch(bt_cx, arch_spring_y, bt_cz - bt_w1/2.0 + 0.2, arch_r, arch_r + 0.45, 0.4, segments=12, axis='Z', mat="Stone_White")
    # X-axis arches (East and West)
    mesh.add_arch(bt_cx + bt_w1/2.0 - 0.2, arch_spring_y, bt_cz, arch_r, arch_r + 0.45, 0.4, segments=12, axis='X', mat="Stone_White")
    mesh.add_arch(bt_cx - bt_w1/2.0 + 0.2, arch_spring_y, bt_cz, arch_r, arch_r + 0.45, 0.4, segments=12, axis='X', mat="Stone_White")

    # Tier 1 upper entablature and cornice
    t1_top_y = t1_base_y + bt_h1
    mesh.add_box(bt_cx, t1_top_y + 0.35, bt_cz, bt_w1 + 0.4, 0.7, bt_w1 + 0.4, "Stone_White")
    mesh.add_box(bt_cx, t1_top_y + 0.85, bt_cz, bt_w1 + 1.0, 0.3, bt_w1 + 1.0, "Stone_White")

    # Tier 2: Square level with clock/medallions & classical windows
    t2_base_y = t1_top_y + 1.0
    bt_w2 = 7.6
    bt_h2 = 5.6
    mesh.add_box(bt_cx, t2_base_y + bt_h2/2.0, bt_cz, bt_w2, bt_h2, bt_w2, "Wall_Cream")
    # Corner quoins
    for sx in (-1, 1):
        for sz in (-1, 1):
            mesh.add_box(bt_cx + sx*(bt_w2/2.0 - 0.6), t2_base_y + bt_h2/2.0, bt_cz + sz*(bt_w2/2.0 - 0.6), 1.25, bt_h2, 1.25, "Stone_White")

    # Round clock / medallion motifs on 4 faces
    clock_y = t2_base_y + bt_h2 * 0.55
    mesh.add_cylinder(bt_cx, clock_y, bt_cz + bt_w2/2.0 + 0.05, 1.1, 1.1, 0.15, segments=20, mat="Stone_White")
    mesh.add_cylinder(bt_cx, clock_y, bt_cz - bt_w2/2.0 - 0.05, 1.1, 1.1, 0.15, segments=20, mat="Stone_White")
    mesh.add_cylinder(bt_cx + bt_w2/2.0 + 0.05, clock_y, bt_cz, 1.1, 1.1, 0.15, segments=20, mat="Stone_White")
    mesh.add_cylinder(bt_cx - bt_w2/2.0 - 0.05, clock_y, bt_cz, 1.1, 1.1, 0.15, segments=20, mat="Stone_White")

    # Tier 2 Cornice
    t2_top_y = t2_base_y + bt_h2
    mesh.add_box(bt_cx, t2_top_y + 0.3, bt_cz, bt_w2 + 0.3, 0.6, bt_w2 + 0.3, "Stone_White")
    mesh.add_box(bt_cx, t2_top_y + 0.7, bt_cz, bt_w2 + 0.8, 0.25, bt_w2 + 0.8, "Stone_White")

    # Tier 3: Open Belfry (Belfry Level / Ярус звона)
    t3_base_y = t2_top_y + 0.8
    bt_w3 = 6.4
    bt_h3 = 6.5
    # 4 Corner Pillars of Belfry
    belfry_pier_s = 1.4
    belfry_offset = bt_w3/2.0 - belfry_pier_s/2.0
    for sx in (-1, 1):
        for sz in (-1, 1):
            px = bt_cx + sx * belfry_offset
            pz = bt_cz + sz * belfry_offset
            mesh.add_box(px, t3_base_y + bt_h3/2.0, pz, belfry_pier_s, bt_h3, belfry_pier_s, "Stone_White")
            # Column on corner
            mesh.add_doric_column(px, t3_base_y, pz + sz*0.4, height=bt_h3*0.88, base_radius=0.35, top_radius=0.30)

    # 4 Grand open arched bell belfries
    belfry_arch_r = (bt_w3 - 2.0 * belfry_pier_s) / 2.0
    belfry_spring_y = t3_base_y + 3.8
    mesh.add_arch(bt_cx, belfry_spring_y, bt_cz + bt_w3/2.0 - 0.2, belfry_arch_r, belfry_arch_r + 0.35, 0.4, segments=12, axis='Z', mat="Stone_White")
    mesh.add_arch(bt_cx, belfry_spring_y, bt_cz - bt_w3/2.0 + 0.2, belfry_arch_r, belfry_arch_r + 0.35, 0.4, segments=12, axis='Z', mat="Stone_White")
    mesh.add_arch(bt_cx + bt_w3/2.0 - 0.2, belfry_spring_y, bt_cz, belfry_arch_r, belfry_arch_r + 0.35, 0.4, segments=12, axis='X', mat="Stone_White")
    mesh.add_arch(bt_cx - bt_w3/2.0 + 0.2, belfry_spring_y, bt_cz, belfry_arch_r, belfry_arch_r + 0.35, 0.4, segments=12, axis='X', mat="Stone_White")

    # Balustrade railing on sills
    mesh.add_box(bt_cx, t3_base_y + 0.5, bt_cz + bt_w3/2.0 - 0.1, bt_w3 - 2*belfry_pier_s, 1.0, 0.2, "Stone_White")
    mesh.add_box(bt_cx, t3_base_y + 0.5, bt_cz - bt_w3/2.0 + 0.1, bt_w3 - 2*belfry_pier_s, 1.0, 0.2, "Stone_White")
    mesh.add_box(bt_cx + bt_w3/2.0 - 0.1, t3_base_y + 0.5, bt_cz, 0.2, 1.0, bt_w3 - 2*belfry_pier_s, "Stone_White")
    mesh.add_box(bt_cx - bt_w3/2.0 + 0.1, t3_base_y + 0.5, bt_cz, 0.2, 1.0, bt_w3 - 2*belfry_pier_s, "Stone_White")

    # Grand Cast Bronze Church Bell hanging in the center of Tier 3
    bell_y = t3_base_y + 3.0
    mesh.add_cylinder(bt_cx, bell_y, bt_cz, 1.0, 0.4, 1.6, segments=20, mat="Bronze_Bell")
    mesh.add_cylinder(bt_cx, bell_y + 1.6, bt_cz, 0.4, 0.3, 0.3, segments=16, mat="Bronze_Bell")
    # Wooden crossbeam holding bell
    mesh.add_box(bt_cx, bell_y + 1.9, bt_cz, 0.4, 0.3, bt_w3 - 0.8, "Wood_Door")

    # Tier 3 Cornice
    t3_top_y = t3_base_y + bt_h3
    mesh.add_box(bt_cx, t3_top_y + 0.3, bt_cz, bt_w3 + 0.3, 0.6, bt_w3 + 0.3, "Stone_White")
    mesh.add_box(bt_cx, t3_top_y + 0.7, bt_cz, bt_w3 + 0.8, 0.3, bt_w3 + 0.8, "Stone_White")

    # Tier 4: Classical Bell-Dome, Needle Spire & Cross
    t4_base_y = t3_top_y + 0.85
    # Stepped attic base
    mesh.add_box(bt_cx, t4_base_y + 0.5, bt_cz, 5.4, 1.0, 5.4, "Stone_White")
    mesh.add_cylinder(bt_cx, t4_base_y + 1.0, bt_cz, 2.6, 2.4, 0.6, segments=24, mat="Stone_White")

    # Elegant curved bell-dome
    bt_dome_y = t4_base_y + 1.6
    bt_dome_r = 2.4
    bt_dome_h = 2.8
    mesh.add_dome(bt_cx, bt_dome_y, bt_cz, radius=bt_dome_r, height=bt_dome_h, lat_segments=12, lon_segments=24, mat="Dome_Metal")

    # Spire base lantern and needle spire
    spire_base_y = bt_dome_y + bt_dome_h - 0.2
    mesh.add_cylinder(bt_cx, spire_base_y, bt_cz, 0.9, 0.8, 1.0, segments=16, mat="Stone_White")
    # Needle spire
    mesh.add_cylinder(bt_cx, spire_base_y + 1.0, bt_cz, 0.75, 0.08, 4.2, segments=16, mat="Dome_Metal")

    # Golden sphere and cross atop Bell Tower
    bt_sphere_y = spire_base_y + 1.0 + 4.2 + 0.3
    mesh.add_dome(bt_cx, bt_sphere_y - 0.3, bt_cz, radius=0.35, height=0.35, lat_segments=6, lon_segments=12, mat="Gold_Cross")
    mesh.add_cylinder(bt_cx, bt_sphere_y - 0.3, bt_cz, 0.35, 0.35, 0.08, segments=12, mat="Gold_Cross")
    mesh.add_orthodox_cross(bt_cx, bt_sphere_y + 0.1, bt_cz, height=2.8, mat="Gold_Cross")

    print(f"Assembly complete! Total vertices: {len(mesh.vertices)}, Total faces: {sum(len(v) for v in mesh.materials.values())}")
    return mesh


# =============================================================================
# EXPORTERS: OBJ / MTL, GLB, STL, HTML VIEWER
# =============================================================================

MATERIAL_DEFS = {
    "Wall_Cream": {
        "Kd": (0.93, 0.90, 0.83),
        "Ka": (0.2, 0.2, 0.2),
        "Ks": (0.1, 0.1, 0.1),
        "Ns": 10.0,
        "roughness": 0.85,
        "metallic": 0.0
    },
    "Stone_White": {
        "Kd": (0.96, 0.95, 0.93),
        "Ka": (0.2, 0.2, 0.2),
        "Ks": (0.15, 0.15, 0.15),
        "Ns": 20.0,
        "roughness": 0.70,
        "metallic": 0.02
    },
    "Stylobate_Granite": {
        "Kd": (0.48, 0.47, 0.46),
        "Ka": (0.15, 0.15, 0.15),
        "Ks": (0.1, 0.1, 0.1),
        "Ns": 15.0,
        "roughness": 0.80,
        "metallic": 0.05
    },
    "Roof_Zinc": {
        "Kd": (0.32, 0.35, 0.38),
        "Ka": (0.15, 0.15, 0.15),
        "Ks": (0.35, 0.35, 0.35),
        "Ns": 40.0,
        "roughness": 0.45,
        "metallic": 0.6
    },
    "Dome_Metal": {
        "Kd": (0.34, 0.39, 0.44),
        "Ka": (0.2, 0.2, 0.2),
        "Ks": (0.5, 0.5, 0.55),
        "Ns": 60.0,
        "roughness": 0.35,
        "metallic": 0.75
    },
    "Gold_Cross": {
        "Kd": (0.92, 0.74, 0.18),
        "Ka": (0.3, 0.25, 0.1),
        "Ks": (0.9, 0.8, 0.3),
        "Ns": 120.0,
        "roughness": 0.18,
        "metallic": 0.95
    },
    "Wood_Door": {
        "Kd": (0.32, 0.20, 0.11),
        "Ka": (0.1, 0.08, 0.05),
        "Ks": (0.1, 0.1, 0.1),
        "Ns": 15.0,
        "roughness": 0.75,
        "metallic": 0.0
    },
    "Window_Glass": {
        "Kd": (0.12, 0.18, 0.24),
        "Ka": (0.1, 0.1, 0.1),
        "Ks": (0.9, 0.9, 0.95),
        "Ns": 150.0,
        "roughness": 0.08,
        "metallic": 0.1,
        "d": 0.85
    },
    "Bronze_Bell": {
        "Kd": (0.58, 0.42, 0.26),
        "Ka": (0.2, 0.15, 0.1),
        "Ks": (0.6, 0.5, 0.3),
        "Ns": 50.0,
        "roughness": 0.4,
        "metallic": 0.85
    },
    "Plaza_Paving": {
        "Kd": (0.65, 0.63, 0.60),
        "Ka": (0.2, 0.2, 0.2),
        "Ks": (0.05, 0.05, 0.05),
        "Ns": 5.0,
        "roughness": 0.9,
        "metallic": 0.0
    },
    "Park_Lawn": {
        "Kd": (0.30, 0.44, 0.22),
        "Ka": (0.1, 0.15, 0.1),
        "Ks": (0.02, 0.02, 0.02),
        "Ns": 5.0,
        "roughness": 0.95,
        "metallic": 0.0
    }
}


def export_obj_mtl(mesh, base_path):
    obj_path = base_path + ".obj"
    mtl_path = base_path + ".mtl"
    mtl_filename = os.path.basename(mtl_path)

    print(f"Writing MTL file: {mtl_path}...")
    with open(mtl_path, "w", encoding="utf-8") as f:
        f.write("# MTL file for Nativity Cathedral of Chisinau\n")
        for mat_name, props in MATERIAL_DEFS.items():
            f.write(f"\nnewmtl {mat_name}\n")
            kd = props["Kd"]
            f.write(f"Kd {kd[0]:.4f} {kd[1]:.4f} {kd[2]:.4f}\n")
            ka = props.get("Ka", (0.2, 0.2, 0.2))
            f.write(f"Ka {ka[0]:.4f} {ka[1]:.4f} {ka[2]:.4f}\n")
            ks = props.get("Ks", (0.2, 0.2, 0.2))
            f.write(f"Ks {ks[0]:.4f} {ks[1]:.4f} {ks[2]:.4f}\n")
            ns = props.get("Ns", 30.0)
            f.write(f"Ns {ns:.1f}\n")
            d = props.get("d", 1.0)
            f.write(f"d {d:.2f}\n")
            f.write("illum 2\n")

    print(f"Writing OBJ file: {obj_path}...")
    with open(obj_path, "w", encoding="utf-8") as f:
        f.write("# 3D Model: Nativity Cathedral of Chisinau (Catedrala Nașterea Domnului)\n")
        f.write(f"mtllib {mtl_filename}\n\n")

        # Vertices
        for v in mesh.vertices:
            f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")

        # UVs
        for vt in mesh.uvs:
            f.write(f"vt {vt[0]:.4f} {vt[1]:.4f}\n")

        # Normals
        for vn in mesh.normals:
            f.write(f"vn {vn[0]:.4f} {vn[1]:.4f} {vn[2]:.4f}\n")

        # Faces grouped by material
        for mat_name, faces in mesh.materials.items():
            if not faces:
                continue
            f.write(f"\ng {mat_name}\n")
            f.write(f"usemtl {mat_name}\n")
            for face in faces:
                (v1, vt1, vn1), (v2, vt2, vn2), (v3, vt3, vn3) = face
                f.write(f"f {v1}/{vt1}/{vn1} {v2}/{vt2}/{vn2} {v3}/{vt3}/{vn3}\n")

    print("OBJ and MTL export finished successfully.")


def export_stl(mesh, stl_path):
    print(f"Writing STL file: {stl_path}...")
    # Binary STL format
    all_triangles = []
    for faces in mesh.materials.values():
        for face in faces:
            (v1, vt1, vn1), (v2, vt2, vn2), (v3, vt3, vn3) = face
            p1 = mesh.vertices[v1 - 1]
            p2 = mesh.vertices[v2 - 1]
            p3 = mesh.vertices[v3 - 1]
            n = mesh.normals[vn1 - 1] if vn1 else (0.0, 1.0, 0.0)
            all_triangles.append((n, p1, p2, p3))

    with open(stl_path, "wb") as f:
        # 80-byte header
        header = b"Nativity Cathedral Chisinau 3D Model STL"
        f.write(header.ljust(80, b"\0"))
        # Number of triangles (uint32)
        f.write(struct.pack("<I", len(all_triangles)))
        for n, p1, p2, p3 in all_triangles:
            # normal, v1, v2, v3 (floats), uint16 attribute byte count
            f.write(struct.pack("<3f", *n))
            f.write(struct.pack("<3f", *p1))
            f.write(struct.pack("<3f", *p2))
            f.write(struct.pack("<3f", *p3))
            f.write(struct.pack("<H", 0))

    print("STL export finished successfully.")


def export_glb(mesh, glb_path):
    """Generates standard glTF 2.0 Binary (.glb) format with PBR materials"""
    print(f"Writing GLB file: {glb_path}...")

    # We will build standard glTF buffers:
    # Per material primitive:
    # positions (vec3 float), normals (vec3 float), uvs (vec2 float), indices (uint32)
    # Collect all unique vertex combinations or direct non-indexed triangles
    
    bin_buffer = bytearray()
    json_accessors = []
    json_buffer_views = []
    json_materials = []
    json_primitives = []
    
    mat_index_map = {}
    for mat_name, props in MATERIAL_DEFS.items():
        mat_idx = len(json_materials)
        mat_index_map[mat_name] = mat_idx
        kd = props["Kd"]
        json_materials.append({
            "name": mat_name,
            "pbrMetallicRoughness": {
                "baseColorFactor": [kd[0], kd[1], kd[2], props.get("d", 1.0)],
                "metallicFactor": props.get("metallic", 0.1),
                "roughnessFactor": props.get("roughness", 0.7)
            },
            "doubleSided": True
        })

    total_vertices_count = 0

    for mat_name, faces in mesh.materials.items():
        if not faces:
            continue
        
        pos_bytes = bytearray()
        norm_bytes = bytearray()
        uv_bytes = bytearray()
        idx_bytes = bytearray()

        min_pos = [float('inf'), float('inf'), float('inf')]
        max_pos = [float('-inf'), float('-inf'), float('-inf')]

        vertex_cache = {}
        indices = []
        vert_count = 0

        for face in faces:
            for v_idx, vt_idx, vn_idx in face:
                key = (v_idx, vt_idx, vn_idx)
                if key in vertex_cache:
                    indices.append(vertex_cache[key])
                else:
                    vertex_cache[key] = vert_count
                    indices.append(vert_count)
                    vert_count += 1

                    p = mesh.vertices[v_idx - 1]
                    n = mesh.normals[vn_idx - 1] if vn_idx else (0.0, 1.0, 0.0)
                    uv = mesh.uvs[vt_idx - 1] if vt_idx else (0.0, 0.0)

                    for c in range(3):
                        if p[c] < min_pos[c]: min_pos[c] = p[c]
                        if p[c] > max_pos[c]: max_pos[c] = p[c]

                    pos_bytes.extend(struct.pack("<3f", *p))
                    norm_bytes.extend(struct.pack("<3f", *n))
                    uv_bytes.extend(struct.pack("<2f", *uv))

        for idx in indices:
            idx_bytes.extend(struct.pack("<I", idx))

        # Pad helper to 4-byte alignment
        def pad_4(b):
            rem = len(b) % 4
            if rem != 0:
                b.extend(b"\x00" * (4 - rem))

        # BufferView & Accessor for Indices
        pad_4(bin_buffer)
        idx_offset = len(bin_buffer)
        bin_buffer.extend(idx_bytes)
        pad_4(bin_buffer)
        idx_bv = len(json_buffer_views)
        json_buffer_views.append({
            "buffer": 0,
            "byteOffset": idx_offset,
            "byteLength": len(idx_bytes),
            "target": 34963 # ELEMENT_ARRAY_BUFFER
        })
        idx_acc = len(json_accessors)
        json_accessors.append({
            "bufferView": idx_bv,
            "byteOffset": 0,
            "componentType": 5125, # UNSIGNED_INT
            "count": len(indices),
            "type": "SCALAR"
        })

        # BufferView & Accessor for Positions
        pos_offset = len(bin_buffer)
        bin_buffer.extend(pos_bytes)
        pad_4(bin_buffer)
        pos_bv = len(json_buffer_views)
        json_buffer_views.append({
            "buffer": 0,
            "byteOffset": pos_offset,
            "byteLength": len(pos_bytes),
            "target": 34962 # ARRAY_BUFFER
        })
        pos_acc = len(json_accessors)
        json_accessors.append({
            "bufferView": pos_bv,
            "byteOffset": 0,
            "componentType": 5126, # FLOAT
            "count": vert_count,
            "type": "VEC3",
            "min": min_pos,
            "max": max_pos
        })

        # BufferView & Accessor for Normals
        norm_offset = len(bin_buffer)
        bin_buffer.extend(norm_bytes)
        pad_4(bin_buffer)
        norm_bv = len(json_buffer_views)
        json_buffer_views.append({
            "buffer": 0,
            "byteOffset": norm_offset,
            "byteLength": len(norm_bytes),
            "target": 34962
        })
        norm_acc = len(json_accessors)
        json_accessors.append({
            "bufferView": norm_bv,
            "byteOffset": 0,
            "componentType": 5126,
            "count": vert_count,
            "type": "VEC3"
        })

        # BufferView & Accessor for UVs
        uv_offset = len(bin_buffer)
        bin_buffer.extend(uv_bytes)
        pad_4(bin_buffer)
        uv_bv = len(json_buffer_views)
        json_buffer_views.append({
            "buffer": 0,
            "byteOffset": uv_offset,
            "byteLength": len(uv_bytes),
            "target": 34962
        })
        uv_acc = len(json_accessors)
        json_accessors.append({
            "bufferView": uv_bv,
            "byteOffset": 0,
            "componentType": 5126,
            "count": vert_count,
            "type": "VEC2"
        })

        json_primitives.append({
            "attributes": {
                "POSITION": pos_acc,
                "NORMAL": norm_acc,
                "TEXCOORD_0": uv_acc
            },
            "indices": idx_acc,
            "material": mat_index_map[mat_name]
        })

    gltf_dict = {
        "asset": {
            "version": "2.0",
            "generator": "Antigravity Cathedral 3D Generator"
        },
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "Cathedral_Ensemble"}],
        "meshes": [{"name": "Cathedral_Ensemble_Mesh", "primitives": json_primitives}],
        "materials": json_materials,
        "accessors": json_accessors,
        "bufferViews": json_buffer_views,
        "buffers": [{"byteLength": len(bin_buffer)}]
    }

    json_str = json.dumps(gltf_dict, separators=(',', ':'))
    json_bytes = json_str.encode('utf-8')
    # Pad JSON chunk to 4-byte boundary with spaces (0x20)
    json_padding = (4 - (len(json_bytes) % 4)) % 4
    json_bytes += b" " * json_padding

    # Pad binary buffer to 4-byte boundary with zeros
    bin_padding = (4 - (len(bin_buffer) % 4)) % 4
    bin_buffer += b"\x00" * bin_padding

    total_size = 12 + 8 + len(json_bytes) + 8 + len(bin_buffer)

    # GLB Header
    glb_header = struct.pack(
        "<4sII",
        b"glTF",      # magic
        2,           # version 2
        total_size   # total file length
    )

    # JSON Chunk Header
    json_chunk_hdr = struct.pack(
        "<II",
        len(json_bytes),
        0x4E4F534A   # 'JSON' in hex
    )

    # BIN Chunk Header
    bin_chunk_hdr = struct.pack(
        "<II",
        len(bin_buffer),
        0x004E4942   # 'BIN\0' in hex
    )

    with open(glb_path, "wb") as f:
        f.write(glb_header)
        f.write(json_chunk_hdr)
        f.write(json_bytes)
        f.write(bin_chunk_hdr)
        f.write(bin_buffer)

    print("GLB export finished successfully.")


def export_html_viewer(html_path, glb_path):
    """Generates an interactive, standalone HTML WebGL viewer using Three.js with full lighting, controls, shadows, and presets.
    Includes Base64 embedded fallback so it can be opened via direct double-click (file://) without CORS errors."""
    print(f"Writing interactive HTML viewer: {html_path}...")
    import base64
    with open(glb_path, "rb") as gf:
        b64_glb = base64.b64encode(gf.read()).decode("ascii")

    html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>3D Модель Кафедрального Собора Кишинева | Catedrala Nașterea Domnului</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
    body {{ background: #181a1f; color: #fff; overflow: hidden; height: 100vh; }}
    #canvas-container {{ width: 100vw; height: 100vh; position: absolute; top: 0; left: 0; }}
    
    /* Header Overlay */
    .header-panel {{
      position: absolute;
      top: 16px;
      left: 20px;
      background: rgba(22, 26, 33, 0.88);
      backdrop-filter: blur(12px);
      padding: 18px 24px;
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.12);
      box-shadow: 0 10px 30px rgba(0,0,0,0.5);
      max-width: 450px;
      z-index: 10;
      pointer-events: auto;
    }}
    .header-panel h1 {{
      font-size: 19px;
      font-weight: 700;
      letter-spacing: -0.3px;
      color: #f7d56e;
      margin-bottom: 6px;
    }}
    .header-panel h2 {{
      font-size: 13px;
      font-weight: 400;
      color: #b0b8c4;
      line-height: 1.4;
      margin-bottom: 12px;
    }}
    .stats-badge {{
      display: inline-flex;
      flex-wrap: wrap;
      gap: 10px;
      font-size: 11px;
      color: #8da1b5;
      background: rgba(255,255,255,0.06);
      padding: 8px 12px;
      border-radius: 6px;
    }}
    .stats-badge span b {{ color: #fff; }}

    /* Controls Panel */
    .controls-panel {{
      position: absolute;
      bottom: 24px;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(22, 26, 33, 0.90);
      backdrop-filter: blur(12px);
      padding: 10px 18px;
      border-radius: 30px;
      border: 1px solid rgba(255, 255, 255, 0.12);
      box-shadow: 0 10px 30px rgba(0,0,0,0.5);
      display: flex;
      gap: 10px;
      align-items: center;
      z-index: 10;
    }}
    .btn {{
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #eee;
      padding: 8px 14px;
      border-radius: 20px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 500;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .btn:hover {{
      background: rgba(247, 213, 110, 0.2);
      color: #f7d56e;
      border-color: rgba(247, 213, 110, 0.4);
      transform: translateY(-1px);
    }}
    .btn.active {{
      background: #f7d56e;
      color: #1a1a1a;
      font-weight: 600;
    }}

    /* Right Sidebar for Camera Presets */
    .presets-panel {{
      position: absolute;
      top: 16px;
      right: 20px;
      background: rgba(22, 26, 33, 0.88);
      backdrop-filter: blur(12px);
      padding: 14px 18px;
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.12);
      box-shadow: 0 10px 30px rgba(0,0,0,0.5);
      display: flex;
      flex-direction: column;
      gap: 8px;
      z-index: 10;
    }}
    .presets-panel .title {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: #8da1b5;
      margin-bottom: 2px;
    }}
    .preset-btn {{
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #ddd;
      padding: 7px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      text-align: left;
      transition: all 0.2s ease;
    }}
    .preset-btn:hover {{
      background: rgba(255, 255, 255, 0.18);
      color: #fff;
    }}

    /* Loading overlay */
    #loading {{
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      font-size: 16px;
      color: #f7d56e;
      background: rgba(0,0,0,0.7);
      padding: 16px 24px;
      border-radius: 8px;
      pointer-events: none;
      transition: opacity 0.4s;
    }}
  </style>
</head>
<body>
  <div id="canvas-container"></div>
  <div id="loading">Загрузка 3D модели...</div>

  <div class="header-panel">
    <h1>Собор Рождества Христова</h1>
    <h2>Кафедральный собор Молдовы (Кишинёв) • Catedrala Nașterea Domnului<br>Архитектор Авраам Мельников (1830–1836)</h2>
    <div class="stats-badge">
      <span>Стиль: <b>Русский Ампир / Классицизм</b></span>
      <span>Портики: <b>4 шестиколонных</b></span>
      <span>Колокольня: <b>4 яруса</b></span>
      <span>Основание: <b>27м × 27м</b></span>
    </div>
  </div>

  <div class="presets-panel">
    <div class="title">Виды камеры</div>
    <button class="preset-btn" onclick="setCameraView('hero')">🏛 Общий ракурс (Ансамбль)</button>
    <button class="preset-btn" onclick="setCameraView('facade')">🚪 Главный портик (Южный)</button>
    <button class="preset-btn" onclick="setCameraView('bell')">🔔 Колокольня (Clopotnița)</button>
    <button class="preset-btn" onclick="setCameraView('dome')">☀️ Купол и барабан (Крупно)</button>
    <button class="preset-btn" onclick="setCameraView('top')">📐 План сверху (Ортогональный)</button>
  </div>

  <div class="controls-panel">
    <button class="btn" id="btn-rotate" onclick="toggleAutoRotate()">🔄 Вращение</button>
    <button class="btn" id="btn-wireframe" onclick="toggleWireframe()">🕸 Сетка</button>
    <button class="btn" id="btn-lighting" onclick="toggleLighting()">☀️ День / Закат</button>
    <button class="btn" onclick="resetCamera()">🎯 Сброс</button>
  </div>

  <!-- Three.js + GLTFLoader + OrbitControls from CDN -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>

  <script>
    const EMBEDDED_GLB_BASE64 = "{b64_glb}";

    let scene, camera, renderer, controls, cathedralModel;
    let dirLight, ambientLight, hemiLight;
    let isWireframe = false;
    let isSunsetTexture = false;

    const views = {{
      hero:   {{ pos: [-55, 38, 90], target: [0, 16, 20] }},
      facade: {{ pos: [0, 14, 38],   target: [0, 12, 16] }},
      bell:   {{ pos: [24, 22, 60],  target: [0, 16, 42] }},
      dome:   {{ pos: [26, 40, 22],  target: [0, 28, 0] }},
      top:    {{ pos: [0, 125, 20],  target: [0, 0, 20] }}
    }};

    function init() {{
      const container = document.getElementById('canvas-container');

      scene = new THREE.Scene();
      scene.background = new THREE.Color(0xdce7f0);
      scene.fog = new THREE.FogExp2(0xdce7f0, 0.005);

      camera = new THREE.PerspectiveCamera(42, window.innerWidth / window.innerHeight, 0.5, 600);
      camera.position.set(...views.hero.pos);

      renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: false, powerPreference: "high-performance" }});
      renderer.setSize(window.innerWidth, window.innerHeight);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.1;
      container.appendChild(renderer.domElement);

      controls = new THREE.OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.05;
      controls.maxPolarAngle = Math.PI / 2 - 0.01;
      controls.minDistance = 5;
      controls.maxDistance = 250;
      controls.target.set(...views.hero.target);

      setupLighting();
      loadModel();

      window.addEventListener('resize', onWindowResize);
      animate();
    }}

    function setupLighting() {{
      ambientLight = new THREE.AmbientLight(0xffffff, 0.65);
      scene.add(ambientLight);

      hemiLight = new THREE.HemisphereLight(0xffffff, 0x8d9ca5, 0.55);
      hemiLight.position.set(0, 80, 0);
      scene.add(hemiLight);

      dirLight = new THREE.DirectionalLight(0xfff6e5, 1.4);
      dirLight.position.set(50, 85, 45);
      dirLight.castShadow = true;
      dirLight.shadow.mapSize.width = 2048;
      dirLight.shadow.mapSize.height = 2048;
      dirLight.shadow.camera.near = 10;
      dirLight.shadow.camera.far = 250;
      dirLight.shadow.bias = -0.0003;
      const d = 60;
      dirLight.shadow.camera.left = -d;
      dirLight.shadow.camera.right = d;
      dirLight.shadow.camera.top = d;
      dirLight.shadow.camera.bottom = -d;
      scene.add(dirLight);

      const fillLight = new THREE.DirectionalLight(0xbad2e8, 0.45);
      fillLight.position.set(-60, 40, -40);
      scene.add(fillLight);
    }}

    function onModelReady(gltf) {{
      cathedralModel = gltf.scene;
      cathedralModel.traverse(function (child) {{
        if (child.isMesh) {{
          child.castShadow = true;
          child.receiveShadow = true;
          if (child.material) {{
            child.material.side = THREE.DoubleSide;
          }}
        }}
      }});
      scene.add(cathedralModel);
      document.getElementById('loading').style.opacity = '0';
      setTimeout(() => document.getElementById('loading').style.display = 'none', 400);
    }}

    function loadModel() {{
      const loader = new THREE.GLTFLoader();
      // Try fetch first, fallback to embedded Base64 data URI
      loader.load('cathedral_chisinau.glb', onModelReady, undefined, function (error) {{
        console.warn('Direct file fetch failed (likely file:// CORS), falling back to embedded Base64 model...');
        try {{
          const binaryString = atob(EMBEDDED_GLB_BASE64);
          const len = binaryString.length;
          const bytes = new Uint8Array(len);
          for (let i = 0; i < len; i++) {{
            bytes[i] = binaryString.charCodeAt(i);
          }}
          loader.parse(bytes.buffer, '', onModelReady, function (parseErr) {{
            console.error('Base64 parse error:', parseErr);
            document.getElementById('loading').innerText = 'Ошибка парсинга модели';
          }});
        }} catch(e) {{
          console.error('Base64 decode failed:', e);
          document.getElementById('loading').innerText = 'Ошибка загрузки 3D модели';
        }}
      }});
    }}

    function toggleAutoRotate() {{
      controls.autoRotate = !controls.autoRotate;
      controls.autoRotateSpeed = 1.0;
      document.getElementById('btn-rotate').classList.toggle('active', controls.autoRotate);
    }}

    function toggleWireframe() {{
      isWireframe = !isWireframe;
      if (cathedralModel) {{
        cathedralModel.traverse(function (child) {{
          if (child.isMesh && child.material) {{
            child.material.wireframe = isWireframe;
          }}
        }});
      }}
      document.getElementById('btn-wireframe').classList.toggle('active', isWireframe);
    }}

    function toggleLighting() {{
      isSunsetTexture = !isSunsetTexture;
      if (isSunsetTexture) {{
        scene.background = new THREE.Color(0xf6aa7b);
        scene.fog.color = new THREE.Color(0xf6aa7b);
        dirLight.color.setHex(0xff9f55);
        dirLight.intensity = 1.6;
        dirLight.position.set(-80, 25, 40);
        ambientLight.color.setHex(0x504040);
        hemiLight.color.setHex(0xffaa88);
      }} else {{
        scene.background = new THREE.Color(0xdce7f0);
        scene.fog.color = new THREE.Color(0xdce7f0);
        dirLight.color.setHex(0xfff6e5);
        dirLight.intensity = 1.4;
        dirLight.position.set(50, 85, 45);
        ambientLight.color.setHex(0xffffff);
        hemiLight.color.setHex(0xffffff);
      }}
      document.getElementById('btn-lighting').classList.toggle('active', isSunsetTexture);
    }}

    function setCameraView(presetName) {{
      const v = views[presetName];
      if (!v) return;
      controls.autoRotate = false;
      document.getElementById('btn-rotate').classList.remove('active');

      const startPos = camera.position.clone();
      const endPos = new THREE.Vector3(...v.pos);
      const startTarget = controls.target.clone();
      const endTarget = new THREE.Vector3(...v.target);

      const duration = 1200;
      const startTime = performance.now();

      function step(now) {{
        const elapsed = now - startTime;
        const t = Math.min(1.0, elapsed / duration);
        const ease = t < 0.5 ? 2*t*t : -1 + (4 - 2*t)*t;

        camera.position.lerpVectors(startPos, endPos, ease);
        controls.target.lerpVectors(startTarget, endTarget, ease);
        controls.update();

        if (t < 1.0) {{
          requestAnimationFrame(step);
        }}
      }}
      requestAnimationFrame(step);
    }}

    function resetCamera() {{
      setCameraView('hero');
    }}

    function onWindowResize() {{
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    }}

    function animate() {{
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    }}

    window.onload = init;
  </script>
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print("HTML viewer export finished successfully.")



def main():
    target_dir = "/Users/user/Downloads/1"
    os.makedirs(target_dir, exist_ok=True)
    os.chdir(target_dir)

    mesh = build_cathedral_ensemble()

    base_name = "cathedral_chisinau"
    export_obj_mtl(mesh, base_name)
    export_glb(mesh, base_name + ".glb")
    export_stl(mesh, base_name + ".stl")
    export_html_viewer("index.html", base_name + ".glb")

    print("\n--- Summary of Generated 3D Files in /Users/user/Downloads/1 ---")
    for fname in [base_name + ".obj", base_name + ".mtl", base_name + ".glb", base_name + ".stl", "index.html"]:
        fpath = os.path.join(target_dir, fname)
        size_kb = os.path.getsize(fpath) / 1024.0
        print(f"✓ {fname:<25} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
