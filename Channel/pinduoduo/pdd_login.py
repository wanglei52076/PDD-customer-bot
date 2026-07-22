"""
拼多多账号异步登录认证
"""
import os
# 必须在导入 playwright 之前设置浏览器路径
from pathlib import Path
from utils.path_utils import get_app_dir
from utils.logger_loguru import get_logger

# 设置 Playwright 浏览器路径
app_dir = get_app_dir()
browsers_path = app_dir / ".browsers"
if browsers_path.exists():
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)
    logger_temp = get_logger("Pdd_login_init")
    logger_temp.info(f"设置 Playwright 浏览器路径: {browsers_path}")
else:
    # 回退到用户目录
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(os.getenv("LOCALAPPDATA", ""), "ms-playwright")

# PyInstaller 打包（frozen）时，Playwright 默认用 inspect.getfile 定位驱动，
# 会指向构建机路径而失效。这里显式接管：node.exe 走环境变量，cli.js 走 monkeypatch。
import sys as _sys
if getattr(_sys, "frozen", False):
    _driver_dir = Path(_sys._MEIPASS) / "playwright" / "driver"
    _node = _driver_dir / "node.exe"
    _cli = _driver_dir / "package" / "cli.js"
    if _node.exists():
        os.environ["PLAYWRIGHT_NODEJS_PATH"] = str(_node)
    if _cli.exists():
        from playwright._impl import _driver as _pw_driver
        _pw_driver.compute_driver_executable = lambda: (
            os.environ.get("PLAYWRIGHT_NODEJS_PATH", str(_node)),
            str(_cli),
        )
del _sys

from http import cookies
import requests
import json
import hashlib
import asyncio
from typing import Optional, Dict, Any, Tuple
import sys
from database import db_manager
from playwright.async_api import async_playwright
from Channel.pinduoduo.utils.API.get_shop_info import GetShopInfo
from Channel.pinduoduo.utils.API.get_user_info import GetUserInfo

class PDDLogin():
    def __init__(self,name,password):
        self.logger = get_logger("Pdd_login")
        self.channel_name = "pinduoduo"  # 渠道名称固定为"pinduoduo"
        self.base_url = "https://mms.pinduoduo.com/login"
        self.name = name
        self.password = password

    # 本地浏览器启动参数（Chrome/Edge 通用）
    _LAUNCH_ARGS = [
        '--disable-gpu',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-blink-features=AutomationControlled',
        '--disable-notifications',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor',
    ]

    async def _launch_context(self, playwright, user_data_dir: str, headless: bool):
        """启动用户本地的浏览器，避免下载 Playwright 自带的 Chromium。

        优先 Google Chrome，其次 Microsoft Edge（Windows 自带）；
        都不可用时抛出明确错误，提示用户安装。
        """
        last_error = None
        for channel in ("chrome", "msedge"):
            try:
                return await playwright.chromium.launch_persistent_context(
                    user_data_dir,
                    channel=channel,
                    headless=headless,
                    args=self._LAUNCH_ARGS,
                )
            except Exception as e:
                last_error = e
                self.logger.warning(f"启动本地浏览器 {channel} 失败: {e}")
        raise RuntimeError(
            "未找到可用的本地浏览器（Chrome/Edge）。请安装 Google Chrome 或 Microsoft Edge 后重试。"
        ) from last_error

    async def login(self, headless=False):
        """使用账号密码登录

        Args:
            headless: 是否使用无头模式（自动回退时使用 True，避免弹出浏览器窗口）

        """
        try:
            # 启动Playwright
            playwright = await async_playwright().start()

            # 创建独立的用户数据目录，避免多实例冲突
            user_data_dir = str(app_dir / "user_data" / self.name)
            self.logger.debug(f"使用用户数据目录: {user_data_dir}")

            # 使用本地浏览器（Chrome/Edge），无需下载 Playwright 自带 Chromium
            context = await self._launch_context(playwright, user_data_dir, headless=headless)
            
            page = await context.new_page()
            
            # 访问登录页面
            await page.goto(self.base_url)
            
            # 点击账号密码登录
            await page.click("div.Common_item__3diIn:has-text('账号登录')")
            
            # 等待页面加载
            await page.wait_for_selector("input[type='text']")
            
            # 输入店铺名
            await page.fill("input[type='text']", self.name)
            
            # 输入密码
            await page.fill("input[type='password']", self.password)
            
            # 点击登录按钮
            await page.click("button:has-text('登录')")
            
            # 等待页面 title等于 拼多多 商家后台，首页或者订单查询
            await page.wait_for_function("() => document.title === '拼多多 商家后台' || document.title === '首页' || document.title === '订单查询'", timeout=30000)
            
            # 获取cookies并转换为字典格式
            cookies_list = await context.cookies()
            # 将playwright格式的cookies列表转换为字典格式，使用安全的get方法
            cookies_dict = {cookie.get('name', ''): cookie.get('value', '') for cookie in cookies_list if cookie.get('name')}
            cookies_json = json.dumps(cookies_dict)
            # 关闭浏览器上下文
            await context.close()
            await playwright.stop()
                
            return cookies_json
            
        except Exception as e:
            self.logger.error(f"登录失败: {str(e)}")
            return False
        
    async def refresh_cookies(self):
        """重新获取cookies，使用已保存的用户数据，无需再次登录

        Returns:
            str: cookies的JSON字符串，如果失败返回False
        """
        playwright = None
        context = None
        try:
            # 启动Playwright
            playwright = await async_playwright().start()

            # 使用相同的用户数据目录（与login保持一致）
            user_data_dir = str(app_dir / "user_data" / self.name)
            self.logger.debug(f"使用用户数据目录刷新cookies: {user_data_dir}")

            # 检查用户数据目录是否存在
            if not os.path.exists(user_data_dir):
                self.logger.error(f"用户数据目录不存在: {user_data_dir}，请先登录")
                return False

            # 使用本地浏览器（Chrome/Edge），无需下载 Playwright 自带 Chromium
            context = await self._launch_context(playwright, user_data_dir, headless=True)

            page = await context.new_page()

            # 访问拼多多商家后台首页，验证登录状态
            await page.goto("https://mms.pinduoduo.com/home/")

            # 等待页面加载，检查是否需要重新登录
            try:
                # 如果页面跳转到登录页面，说明登录状态已失效
                await page.wait_for_url("**/login**", timeout=5000)
                self.logger.warning("登录状态已失效，需要重新登录")
                return False
            except asyncio.TimeoutError:
                # 没有跳转到登录页面，说明登录状态有效
                pass

            # 获取最新的cookies
            cookies_list = await context.cookies()
            cookies_dict = {cookie.get('name', ''): cookie.get('value', '') for cookie in cookies_list if cookie.get('name')}
            cookies_json = json.dumps(cookies_dict)

            self.logger.info(f"成功刷新账号 '{self.name}' 的cookies")
            return cookies_json

        except Exception as e:
            self.logger.error(f"刷新cookies失败: {str(e)}")
            return False
        finally:
            if context:
                await context.close()
            if playwright:
                try:
                    await playwright.stop()
                except Exception:
                    pass

    def Set_user_info(self,cookies_json):
        user_info = GetUserInfo(cookies_json)
        result = user_info.get_user_info()
        if result is False:
            self.logger.error("获取用户信息失败")
            return None, None, None
        user_id, user_name, mall_id = result
        return user_id, user_name, mall_id

    def Set_shop_info(self,cookies_json):
        shop_info = GetShopInfo(cookies_json)
        result = shop_info.get_shop_info()
        if result is False:
            self.logger.error("获取店铺信息失败")
            return None, None, None
        shop_id, shop_name, mallLogo = result
        return shop_id, shop_name, mallLogo
    
async def login_pdd(name, password, headless=False):
    """
    使用账号密码登录并返回账号、店铺信息，不直接操作数据库。
    如果登录成功，返回包含详细信息的字典。
    如果登录失败，返回 False。

    :param name: 用户名
    :param password: 密码
    :param headless: 是否使用无头模式（默认 False，自动回退时传 True）
    :return: dict or bool
    """
    pdd_login = PDDLogin(name=name, password=password)
    cookies_json = await pdd_login.login(headless=headless)
    if not cookies_json:
        pdd_login.logger.error(f"账号 '{name}' 登录失败，未能获取cookies")
        return False

    try:
        # 获取用户信息和店铺信息
        user_id, user_name, mall_id = pdd_login.Set_user_info(cookies_json)
        shop_id, shop_name, mallLogo = pdd_login.Set_shop_info(cookies_json)
        
        # 检查是否成功获取到必要信息
        if user_id is None or shop_id is None:
            pdd_login.logger.error(f"账号 '{name}' 登录成功，但获取用户信息或店铺信息失败")
            return False

        pdd_login.logger.info(f"账号 '{name}' 登录成功，获取到店铺: {shop_name}({shop_id})")

        # 登录成功，返回包含所有信息的字典
        return {
            "channel_name": pdd_login.channel_name,
            "shop_id": shop_id,
            "shop_name": shop_name,
            "shop_logo": mallLogo,
            "user_id": user_id,
            "username": name,  # 使用传入的登录名
            "password": password, # 使用传入的密码
            "cookies": cookies_json,
        }
    except Exception as e:
        pdd_login.logger.error(f"账号 '{name}' 登录成功，但在处理后续信息时出错: {e}")
        return False

async def refresh_pdd_cookies(name, password=None):
    """
    刷新拼多多账号的cookies，使用已保存的用户数据，无需再次输入账号密码。
    如果刷新成功，返回包含最新cookies的字典。
    如果刷新失败（如登录状态已失效），返回 False。

    :param name: 用户名
    :param password: 密码（可选，仅用于创建PDDLogin实例）
    :return: dict or bool
    """
    pdd_login = PDDLogin(name=name, password=password or "")
    cookies_json = await pdd_login.refresh_cookies()
    
    if not cookies_json:
        pdd_login.logger.error(f"账号 '{name}' cookies刷新失败")
        return False

    try:
        # 获取用户信息和店铺信息
        user_id, user_name, mall_id = pdd_login.Set_user_info(cookies_json)
        shop_id, shop_name, mallLogo = pdd_login.Set_shop_info(cookies_json)
        
        # 检查是否成功获取到必要信息
        if user_id is None or shop_id is None:
            pdd_login.logger.error(f"账号 '{name}' cookies刷新成功，但获取用户信息或店铺信息失败")
            return False

        pdd_login.logger.info(f"账号 '{name}' cookies刷新成功，店铺: {shop_name}({shop_id})")

        # 刷新成功，返回包含最新信息的字典
        return {
            "channel_name": pdd_login.channel_name,
            "shop_id": shop_id,
            "shop_name": shop_name,
            "shop_logo": mallLogo,
            "user_id": user_id,
            "username": name,
            "password": password or "",
            "cookies": cookies_json,
        }
    except Exception as e:
        pdd_login.logger.error(f"账号 '{name}' cookies刷新成功，但在处理后续信息时出错: {e}")
        return False

