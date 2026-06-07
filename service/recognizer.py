# pet_recognizer.py
import numpy as np
from PIL import Image
import tflite_runtime.interpreter as tflite

class PetRecognizer:
    """宠物识别类 - 只负责图片识别，不涉及摄像头和舵机"""
    
    def __init__(self, model_path: str = 'mobilenet_v1_1.0_224_quant.tflite', label_path: str = 'labels_mobilenet_quant_v1_224.txt'):
        """
        初始化识别器
        
        Args:
            model_path: TensorFlow Lite 模型路径
            label_path: 标签文件路径
        """
        self.model_path = model_path
        self.label_path = label_path
        
        # 加载标签
        self.labels, self.get_main_class = self._load_labels(label_path)
        
        # 加载模型
        self.interpreter = tflite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        
        # 获取输入输出信息
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.input_index = self.input_details[0]['index']
        self.output_index = self.output_details[0]['index']
        
        # 获取输入尺寸
        self.input_height = self.input_details[0]['shape'][1]
        self.input_width = self.input_details[0]['shape'][2]
    
    def _load_labels(self, path: str):
        """加载标签文件"""
        with open(path, "r") as f:
            label_list = [line.strip() for line in f.readlines()]
        
        def get_main_class(idx):
            if 281 <= idx <= 287:
                return "cat"
            elif 151 <= idx <= 157:
                return "dog"
            else:
                return "other"
        
        return label_list, get_main_class
    
    def recognize_image(self, img_path: str):
        """
        识别单张图片
        
        Args:
            img_path: 图片路径
        
        Returns:
            tuple: (label, score) 例如 ("cat", 0.95)
        """
        # 加载并预处理图片
        image = Image.open(img_path).convert("RGB")
        image = image.resize((self.input_width, self.input_height))
        input_data = np.expand_dims(image, axis=0)
        
        # 推理
        self.interpreter.set_tensor(self.input_index, input_data)
        self.interpreter.invoke()
        
        # 获取结果
        output_data = self.interpreter.get_tensor(self.output_index)
        output_data = np.squeeze(output_data)
        top_index = np.argmax(output_data)
        score = float(output_data[top_index] / 255.0)
        label = self.get_main_class(top_index)
        
        return label, score
    
    def recognize_multiple(self, img_paths: list):
        """
        识别多张图片，返回投票结果
        
        Args:
            img_paths: 图片路径列表
        
        Returns:
            dict: {
                'final_label': 'cat',
                'all_labels': ['cat', 'cat', 'dog'],
                'scores': [0.95, 0.92, 0.45],
                'img_paths': [...]
            }
        """
        all_labels = []
        all_scores = []
        
        for path in img_paths:
            label, score = self.recognize_image(path)
            all_labels.append(label)
            all_scores.append(score)
        
        # 投票
        if all_labels:
            final_label = max(all_labels, key=all_labels.count)
        else:
            final_label = "unknown"
        
        return {
            'label': final_label,
            'all_labels': all_labels,
            'scores': all_scores,
            'img_paths': img_paths
        }