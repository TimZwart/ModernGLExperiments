#version 330
in vec3 v_color;
in vec3 v_world_pos;
out vec4 f_color;
uniform vec3 eye_position;

void main() {
    // Render vertex color as-is (no channel bias or transparency)
    f_color = vec4(v_color, 1.0);
}