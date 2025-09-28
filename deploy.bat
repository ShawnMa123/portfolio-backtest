@echo off
REM Windows 简化部署脚本
setlocal enabledelayedexpansion

REM 显示使用方法
if "%1"=="" goto :usage
if "%1"=="--help" goto :usage

REM 检查Docker
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Docker未安装，请先安装Docker Desktop
    exit /b 1
)

where docker-compose >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Docker Compose未安装，请先安装Docker Compose
    exit /b 1
)

echo [INFO] Docker环境检查通过

REM 根据参数执行操作
if "%1"=="--full" goto :deploy_full
if "%1"=="--hybrid" goto :deploy_hybrid
if "%1"=="--stop" goto :stop_services
if "%1"=="--status" goto :show_status
if "%1"=="--clean" goto :clean_all

echo [ERROR] 未知选项: %1
goto :usage

:deploy_full
echo [INFO] 开始完全Docker化部署...
echo [INFO] 停止现有服务...
docker-compose -f docker-compose.full.yml down 2>nul

echo [INFO] 构建应用镜像...
docker-compose -f docker-compose.full.yml build

echo [INFO] 启动所有服务...
docker-compose -f docker-compose.full.yml up -d

echo [INFO] 等待服务启动...
timeout /t 10 /nobreak >nul

echo [INFO] 检查服务状态...
docker-compose -f docker-compose.full.yml ps

echo [INFO] 完全Docker化部署完成！
echo [INFO] 访问地址: http://localhost:5000
echo [INFO] API文档: http://localhost:5000/api/docs/
echo [INFO] 健康检查: http://localhost:5000/health
goto :end

:deploy_hybrid
echo [INFO] 开始混合部署...
echo [INFO] 停止现有中间件服务...
docker-compose -f docker-compose.hybrid.yml down 2>nul

echo [INFO] 启动中间件服务（数据库、Redis、代理池）...
docker-compose -f docker-compose.hybrid.yml up -d

echo [INFO] 等待中间件启动...
timeout /t 15 /nobreak >nul

echo [INFO] 检查中间件状态...
docker-compose -f docker-compose.hybrid.yml ps

echo [INFO] 混合部署中间件启动完成！
echo.
echo [INFO] 现在需要手动启动Python应用:
echo [INFO] 1. 复制环境配置: copy .env.hybrid .env
echo [INFO] 2. 安装依赖: pip install -r requirements.txt
echo [INFO] 3. 启动Celery: python scripts/celery_worker.py
echo [INFO] 4. 启动应用: python app.py
goto :end

:stop_services
echo [INFO] 停止所有服务...
docker-compose -f docker-compose.full.yml down 2>nul
docker-compose -f docker-compose.hybrid.yml down 2>nul
echo [INFO] 所有服务已停止
goto :end

:show_status
echo [INFO] === 完全Docker化部署状态 ===
docker-compose -f docker-compose.full.yml ps 2>nul
if %errorlevel% neq 0 echo [WARNING] 完全Docker化部署未运行

echo.
echo [INFO] === 混合部署状态 ===
docker-compose -f docker-compose.hybrid.yml ps 2>nul
if %errorlevel% neq 0 echo [WARNING] 混合部署未运行
goto :end

:clean_all
echo [WARNING] 这将删除所有容器、镜像和数据！
set /p confirm="确认清理所有数据？ (y/N): "
if /i "!confirm!"=="y" (
    echo [INFO] 清理所有容器和数据...
    docker-compose -f docker-compose.full.yml down -v --rmi all 2>nul
    docker-compose -f docker-compose.hybrid.yml down -v --rmi all 2>nul
    docker container prune -f 2>nul
    docker image prune -f 2>nul
    docker volume prune -f 2>nul
    echo [INFO] 清理完成
) else (
    echo [INFO] 取消清理操作
)
goto :end

:usage
echo 使用方法: %0 [选项]
echo.
echo 选项:
echo   --full      完全Docker化部署（推荐）
echo   --hybrid    混合部署（Python手动 + Docker中间件）
echo   --stop      停止所有服务
echo   --clean     清理所有容器和数据
echo   --status    查看服务状态
echo   --help      显示此帮助信息
goto :end

:end
endlocal