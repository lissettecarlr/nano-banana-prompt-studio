# Web版本

## 使用

```bash
cd src/web
pip install -r requirements.txt
python start.py
```

## docker
在项目根目录
```bash
docker build -f web_dockerfile -t nano-banana-web:v0.1.1 .

# 运行容器
docker run --rm --name nano-banana-web -p 5000:5000 nano-banana-web:v0.1.1
```