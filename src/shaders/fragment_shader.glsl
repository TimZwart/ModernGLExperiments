#version 330
in vec3 v_color;
in vec3 v_world_pos;
out vec4 f_color;
uniform vec3 eye_position;

void main() {
    float distance_to_eye = length(v_world_pos - eye_position);
    
    // Calculate attenuation factor based on distance
    float attenuation = 1.0 / (1.0 + 0.1 * distance_to_eye + 0.05 * distance_to_eye * distance_to_eye);
    
    // Create a new variable for the modified color
    vec3 modified_color = v_color;
    modified_color.r *= 0.5 + 0.5 * sin(distance_to_eye);
    
    // Combine base color with distance-based attenuation
    vec3 final_color = modified_color * (0.2 + 0.8 * attenuation);
    
    f_color = vec4(modified_color, 1.0);
}