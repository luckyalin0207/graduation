"""
机器学习薪资预测模块
使用随机森林回归模型进行薪资预测
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from jobs.models import JobData
import pickle
import os
import warnings
from django.conf import settings

# 过滤sklearn的特征名称警告
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')
warnings.filterwarnings('ignore', message='X has feature names')


class SalaryPredictor:
    """薪资预测器"""
    
    def __init__(self):
        self.model = None
        self.encoders = {}
        self.feature_columns = ['city', 'education', 'experience', 'key_word']
        self.model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'salary_model.pkl')
        self.encoders_path = os.path.join(settings.BASE_DIR, 'ml_models', 'encoders.pkl')
        
        # 确保模型目录存在
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
    
    def _prepare_data(self, jobs_queryset):
        """准备训练数据"""
        data = []
        for job in jobs_queryset:
            if job.salary_max and job.salary_max > 0:
                data.append({
                    'city': job.city or '未知',
                    'education': job.education or '不限',
                    'experience': job.experience or '不限',
                    'key_word': job.key_word or '其他',
                    'salary': float(job.salary_max)
                })
        
        if not data:
            return None, None
        
        df = pd.DataFrame(data)
        return df, df['salary']
    
    def _encode_features(self, df, fit=False):
        """对类别特征进行编码"""
        df_encoded = df.copy()
        
        for col in self.feature_columns:
            if col not in df_encoded.columns:
                continue
                
            if fit:
                # 训练时创建新的编码器
                self.encoders[col] = LabelEncoder()
                df_encoded[col] = self.encoders[col].fit_transform(df_encoded[col].astype(str))
            else:
                # 预测时使用已有的编码器
                if col in self.encoders:
                    # 处理未见过的类别
                    def safe_transform(value):
                        try:
                            return self.encoders[col].transform([str(value)])[0]
                        except ValueError:
                            # 未见过的类别，返回最常见类别的编码
                            return 0
                    
                    df_encoded[col] = df_encoded[col].apply(safe_transform)
                else:
                    df_encoded[col] = 0
        
        return df_encoded
    
    def train(self, min_samples=50):
        """训练模型"""
        # 获取有薪资数据的职位
        jobs = JobData.objects.exclude(salary_max__isnull=True).exclude(salary_max=0)
        
        if jobs.count() < min_samples:
            return False, f"数据量不足，至少需要 {min_samples} 条数据，当前只有 {jobs.count()} 条"
        
        # 准备数据
        df, y = self._prepare_data(jobs)
        if df is None or len(df) < min_samples:
            return False, "有效数据不足"
        
        # 编码特征
        X = self._encode_features(df[self.feature_columns], fit=True)
        
        # 转换为numpy数组以避免特征名称警告
        X_array = X.values if isinstance(X, pd.DataFrame) else X
        y_array = y.values if isinstance(y, pd.Series) else y
        
        # 训练模型
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_array, y_array)
        
        # 保存模型和编码器
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.model, f)
            with open(self.encoders_path, 'wb') as f:
                pickle.dump(self.encoders, f)
        except Exception as e:
            return False, f"模型保存失败: {str(e)}"
        
        # 计算模型得分
        score = self.model.score(X_array, y_array)
        return True, f"模型训练成功，R² 得分: {score:.4f}"
    
    def load_model(self):
        """加载已训练的模型"""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.encoders_path):
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                with open(self.encoders_path, 'rb') as f:
                    self.encoders = pickle.load(f)
                return True
        except Exception:
            pass
        return False
    
    def predict(self, city='', education='', experience='', job_type=''):
        """预测薪资"""
        # 尝试加载模型
        if self.model is None:
            if not self.load_model():
                # 如果没有模型，尝试训练一个
                success, msg = self.train()
                if not success:
                    return None, msg
        
        # 准备预测数据
        predict_data = pd.DataFrame([{
            'city': city if city else '未知',
            'education': education if education else '不限',
            'experience': experience if experience else '不限',
            'key_word': job_type if job_type else '其他'
        }])
        
        # 编码特征
        X_predict = self._encode_features(predict_data[self.feature_columns], fit=False)
        
        # 转换为numpy数组以避免特征名称警告
        X_predict_array = X_predict.values if isinstance(X_predict, pd.DataFrame) else X_predict
        
        # 预测
        try:
            predicted_salary = self.model.predict(X_predict_array)[0]
            # 确保预测值在合理范围内
            predicted_salary = max(3.0, min(predicted_salary, 200.0))
            return predicted_salary, "预测成功"
        except Exception as e:
            return None, f"预测失败: {str(e)}"
    
    def get_confidence_interval(self, city='', education='', experience='', job_type=''):
        """获取预测的置信区间（使用森林中所有树的预测）"""
        if self.model is None:
            if not self.load_model():
                return None, None
        
        predict_data = pd.DataFrame([{
            'city': city if city else '未知',
            'education': education if education else '不限',
            'experience': experience if experience else '不限',
            'key_word': job_type if job_type else '其他'
        }])
        
        X_predict = self._encode_features(predict_data[self.feature_columns], fit=False)
        
        # 转换为numpy数组
        X_predict_array = X_predict.values if isinstance(X_predict, pd.DataFrame) else X_predict
        
        try:
            # 获取所有树的预测
            predictions = np.array([tree.predict(X_predict_array.reshape(1, -1))[0] for tree in self.model.estimators_])
            lower = np.percentile(predictions, 25)
            upper = np.percentile(predictions, 75)
            return max(3.0, lower), min(upper, 200.0)
        except Exception:
            return None, None


# 全局预测器实例
_predictor = None

def get_predictor():
    """获取预测器单例"""
    global _predictor
    if _predictor is None:
        _predictor = SalaryPredictor()
    return _predictor

