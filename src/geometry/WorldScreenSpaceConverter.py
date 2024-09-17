import numpy as np
class WorldScreenSpaceConverter:
    def __init__(self, width, height, mvp, world_coords, camera):
        self.width = width
        self.height = height
        self.mvp = mvp
        self.world_coords = world_coords
        self.camera = camera
    def compute(self):
        self._print_before_clipspace_conversion()
        clip_coords = self._toClipSpace()
        self._print_assert_after_clip_coords(clip_coords)
        normalized_device_coordinates = self._toNormalizedDeviceCoordinates(clip_coords)
        self._asserts_after_normalized_device_coordinates(normalized_device_coordinates)
        screen_coords = self._toScreenCoordinates(normalized_device_coordinates)
        self._assert_and_print_after_screen_coords(screen_coords, clip_coords, normalized_device_coordinates)
        return screen_coords

    def _toClipSpace(self):
        return np.dot(np.column_stack((self.world_coords, np.ones(self.world_coords.shape[0]))), np.array(self.mvp))

    def _toNormalizedDeviceCoordinates(self, clip_coords):
        return clip_coords[:, :3] / clip_coords[:, 3:]

    def _toScreenCoordinates(self, normalized_device_coordinates):
        return np.column_stack((
            (normalized_device_coordinates[:, 0] + 1) * 0.5 * self.width,
            (1 - normalized_device_coordinates[:, 1]) * 0.5 * self.height
        ))

    def _print_before_clipspace_conversion(self):
        print("Camera position:", self.camera.eye)
        print("Look at position:", self.camera.look_at)
        print("Up vector:", self.camera.up)

        print("World coordinates:")
        for i, coord in enumerate(self.world_coords):
            print(f"Vertex {i}: {coord}")

        print("\nMVP matrix:")
        print(self.mvp)

    def _print_assert_after_clip_coords(self, clip_coords):
        print("\nClip coordinates:")
        for i, coord in enumerate(clip_coords):
            print(f"Vertex {i}: {coord}")

        # Check clip space coordinates
        assert np.all(np.abs(clip_coords[:, :3]) <= np.abs(clip_coords[:, 3:4])), "Clip space coordinates are outside the canonical view volume"
    def _asserts_after_normalized_device_coordinates(self, ndc_coords):
        assert np.all(np.abs(ndc_coords) <= 1), "NDC coordinates are outside the [-1, 1] range"


    def _assert_and_print_after_screen_coords(self, screen_coords, clip_coords, ndc_coords):
        assert np.all(screen_coords >= 0) and np.all(screen_coords[:, 0] <= self.width) and np.all(
            screen_coords[:, 1] <= self.height), "Screen coordinates are outside the screen boundaries"

        print(f"World coordinates shape: {self.world_coords.shape}")
        print(f"Screen coordinates shape: {screen_coords.shape}")
        print(
            f"Clip coordinate ranges: X ({clip_coords[:, 0].min():.2f}, {clip_coords[:, 0].max():.2f}), Y ({clip_coords[:, 1].min():.2f}, {clip_coords[:, 1].max():.2f}), Z ({clip_coords[:, 2].min():.2f}, {clip_coords[:, 2].max():.2f}), W ({clip_coords[:, 3].min():.2f}, {clip_coords[:, 3].max():.2f})")
        print(
            f"NDC coordinate ranges: X ({ndc_coords[:, 0].min():.2f}, {ndc_coords[:, 0].max():.2f}), Y ({ndc_coords[:, 1].min():.2f}, {ndc_coords[:, 1].max():.2f}), Z ({ndc_coords[:, 2].min():.2f}, {ndc_coords[:, 2].max():.2f})")
        print(
            f"Screen coordinate ranges: X ({screen_coords[:, 0].min():.2f}, {screen_coords[:, 0].max():.2f}), Y ({screen_coords[:, 1].min():.2f}, {screen_coords[:, 1].max():.2f})")
