#version 330
in vec3 in_vert;
in vec3 in_color;
out vec3 v_color;
out vec3 v_world_pos;
uniform mat4 mvp;
uniform mat4 model;

void main() {
    gl_Position = mvp * vec4(in_vert, 1.0);
    v_color = in_color;
    v_world_pos = (model * vec4(in_vert, 1.0)).xyz;
}