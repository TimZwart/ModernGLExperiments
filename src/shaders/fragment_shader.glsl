#version 330
in vec3 v_color;
in vec3 v_world_pos;
out vec4 f_color;
uniform vec3 eye_position;
uniform int view_mode; // 0 normal, 1 distance_fade
uniform float min_mesh_distance;
uniform float max_mesh_distance;

void main() {
    if (view_mode == 1) {
        float dist = length(v_world_pos - eye_position);
        float range = max(1e-6, max_mesh_distance - min_mesh_distance);
        float t = (dist - min_mesh_distance) / range;
        float factor = clamp(1.0 - t, 0.0, 1.0);
        f_color = vec4(v_color * factor, 1.0);
    } else {
        // Render vertex color as-is (no channel bias or transparency)
        f_color = vec4(v_color, 1.0);
    }
}