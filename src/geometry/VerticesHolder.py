class VerticesHolder:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VerticesHolder, cls).__new__(cls)
            cls._instance.vertices = []
        return cls._instance
verticesHolder = VerticesHolder()