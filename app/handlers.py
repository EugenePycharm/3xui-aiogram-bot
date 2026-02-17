from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice, ContentType
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart, CommandObject
from app.keyboards import main_menu, inline_plans, profile_keyboard
import app.database.requests as rq
from app.api.three_x_ui import ThreeXUIClient
from app.database.models import Server, Plan, SubscriptionStatus
import os
from datetime import datetime, timedelta
import json
import urllib.parse
from app.utils import generate_vless_link, get_subscription_link

router = Router()

BOT_USERNAME = "VPNLESS_VPN_BOT"

async def issue_subscription(tg_id: int, plan: Plan, server: Server, bot: Bot):
    """
    Activated when payment is confirmed or balance is used.
    """
    client = ThreeXUIClient(server.api_url, server.username, server.password)
    if await client.login():
        inbounds_resp = await client.get_inbounds()
        if inbounds_resp.get('success'):
            inbounds = inbounds_resp.get('obj', [])
            if inbounds:
                target_inbound = inbounds[0]
                email = f"user_{tg_id}_{plan.name.replace(' ', '_')}_{int(datetime.now().timestamp())}"
                expiry_time = int((datetime.now() + timedelta(days=plan.duration_days)).timestamp() * 1000)
                
                success, _, uuid = await client.add_client(
                    inbound_id=target_inbound['id'],
                    email=email,
                    total_gb=plan.data_limit_gb,
                    expiry_time=expiry_time,
                    sub_id=email
                )
                if success:
                    base_host = server.api_url.split('//')[1].split('/')[0].split(':')[0]
                    vless_link = generate_vless_link(uuid, base_host, 443, email, target_inbound.get('streamSettings'))
                    
                    # Check for port override in stream settings
                    stream_settings = json.loads(target_inbound.get('streamSettings', '{}'))
                    external_proxies = stream_settings.get('externalProxy', [])
                    port = 443
                    if external_proxies:
                        port = external_proxies[0].get('port', 443)
                    
                    # Regenerate with correct port if needed
                    vless_link = generate_vless_link(uuid, base_host, port, email, target_inbound.get('streamSettings'))
                    
                    sub = await rq.create_subscription(tg_id, server.id, plan.id, uuid, email, target_inbound['id'], vless_link)
                    
                    sub_link = get_subscription_link(base_host, email)
                    
                    from aiogram.utils.keyboard import InlineKeyboardBuilder
                    from aiogram.types import InlineKeyboardButton
                    builder = InlineKeyboardBuilder()
                    builder.row(InlineKeyboardButton(text="📥 Моя подписка", url=sub_link))
                    builder.row(InlineKeyboardButton(text="🔑 Посмотреть мой ключ", callback_data="view_key"))
                    
                    msg_text = (
                        f"✅ **Подписка активирована!**\n"
                        f"Тариф: {plan.name}\n\n"
                        f"Нажмите на кнопки ниже для доступа."
                    )
                    await bot.send_message(tg_id, msg_text, parse_mode="Markdown", reply_markup=builder.as_markup())
                    await client.close()
                    return True
    await client.close()
    return False


@router.message(CommandStart())
async def start(message: Message, command: CommandObject, bot: Bot):
    referrer_id = None
    args = command.args
    
    if args and args.isdigit():
        referrer_id = int(args)
        if referrer_id == message.from_user.id:
            referrer_id = None # Can't refer self

    # Flag: was this user created in this /start call
    is_new = await rq.add_user(
        tg_id=message.from_user.id, 
        name=message.from_user.first_name, 
        surname=message.from_user.last_name, 
        user_tag=message.from_user.username,
        referrer_id=referrer_id
    )
    
    if is_new:
        msg = f"👋 Привет, {message.from_user.first_name}!\nДобро пожаловать в VPNLESS."
        
        # Grant Trial if new
        trial_plan = await rq.get_trial_plan()
        server = await rq.get_active_server()
        
        if trial_plan and server:
            client = ThreeXUIClient(server.api_url, server.username, server.password)
            if await client.login():
                 # Use first inbound
                 inbounds_resp = await client.get_inbounds()
                 if inbounds_resp.get('success'):
                     inbounds = inbounds_resp.get('obj', [])
                     if inbounds:
                         target_inbound = inbounds[0]
                         email = f"user_{message.from_user.id}_trial"
                         # Set 7 days expiry in ms
                         expiry_time = int((datetime.now() + timedelta(days=7)).timestamp() * 1000)

                         success, _, uuid = await client.add_client(
                             inbound_id=target_inbound['id'],
                             email=email,
                             total_gb=trial_plan.data_limit_gb,
                             expiry_time=expiry_time,
                             sub_id=email
                         )
                         if success:
                             base_host = server.api_url.split('//')[1].split('/')[0].split(':')[0]
                             
                             # Check for port override
                             stream_settings = json.loads(target_inbound.get('streamSettings', '{}'))
                             external_proxies = stream_settings.get('externalProxy', [])
                             port = 443
                             if external_proxies:
                                 port = external_proxies[0].get('port', 443)
                             
                             # Use unified generator
                             vless_link = generate_vless_link(uuid, base_host, port, email, target_inbound.get('streamSettings'))
                             
                             await rq.create_subscription(message.from_user.id, server.id, trial_plan.id, uuid, email, target_inbound['id'], vless_link, is_trial=True)
                             
                             sub_link = get_subscription_link(base_host, email)
                             
                             msg += f"\n\n🎁 **Вам начислен пробный период на 7 дней!**\n\nМоя подписка: [Нажать]({sub_link})\nВаш ключ в профиле."


            await client.close()

        # Reward Referrer (only when a new user registers by link)
        if referrer_id:
            # Load referrer user from DB
            ref_user = await rq.select_user(referrer_id)

            if ref_user:
                # If referrer has not yet received the subscription bonus,
                # extend their existing 7‑day subscription (if есть) на 7 дней
                # и пометить, что бонус уже получен.
                if not ref_user.received_bonus:
                    # Пытаемся найти его активную подписку (ту самую, выданную при регистрации)
                    ref_sub = await rq.get_user_subscription(referrer_id)

                    # Есть активная подписка — продлеваем её на 7 дней и в 3x‑ui, и в БД
                    if ref_sub and server:
                        new_expires_at = ref_sub.expires_at + timedelta(days=7)
                        new_expiry_time_ms = int(new_expires_at.timestamp() * 1000)

                        ref_client = ThreeXUIClient(server.api_url, server.username, server.password)
                        if await ref_client.login():
                            # обновляем клиента через /panel/api/inbounds/updateClient/{uuid}
                            updated = await ref_client.update_client(
                                inbound_id=ref_sub.inbound_id,
                                client_uuid=ref_sub.uuid,
                                email=ref_sub.email,
                                total_gb=trial_plan.data_limit_gb if trial_plan else 0,
                                expiry_time=new_expiry_time_ms,
                                enable=True,
                                sub_id=ref_sub.email
                            )

                            if updated:
                                # продлеваем срок действия в БД
                                await rq.extend_subscription(ref_sub.id, 7)

                                # помечаем, что бонус использован
                                await rq.set_user_bonus_received(ref_user.id)

                                # уведомляем реферала
                                try:
                                    base_host = server.api_url.split('//')[1].split('/')[0].split(':')[0]
                                    sub_link = get_subscription_link(base_host, ref_sub.email)
                                    await bot.send_message(
                                        referrer_id,
                                        f"🎉 По вашей ссылке зарегистрировался друг!\n"
                                        f"Ваша подписка продлена на 7 дней.\n\n"
                                        f"Моя подписка: [Нажать]({sub_link})",
                                        parse_mode="Markdown"
                                    )
                                except:
                                    pass

                        await ref_client.close()
                    # Если активной подписки нет (например, её удалили), можно при желании
                    # fallback‑ом создать новую, но по требованиям главное — продлевать существующую.

                # If referrer already received the 7‑day bonus earlier,
                # give them 10 RUB instead.
                else:
                    await rq.add_balance(referrer_id, 10)
                    try:
                        await bot.send_message(
                            referrer_id,
                            "🎉 По вашей ссылке зарегистрировался друг! Вам начислено 10 рублей на баланс."
                        )
                    except:
                        pass

    else:
        msg = f"С возвращением, {message.from_user.first_name}!"

    await message.answer(msg, reply_markup=main_menu, parse_mode="Markdown")

@router.message(F.text == '👤 Профиль')
async def profile(message: Message):
    user = await rq.select_user(message.from_user.id)
    sub = await rq.get_user_subscription(user.tg_id)
    referrals_count = await rq.get_referrals_count(user.id) # user.id is PK, referrer_id stores PK
    
    text = f"👤 **Профиль**\n\n"
    text += f"🆔 ID: `{user.tg_id}`\n"
    text += f"💰 Баланс: {user.balance} RUB\n"
    text += f"👥 Приглашено друзей: {referrals_count}\n\n"
    
    markup = await profile_keyboard()
    
    if sub:
        expiry = sub.expires_at.strftime("%d.%m.%Y")
        days_left = (sub.expires_at - datetime.now()).days
        base_host = sub.server.api_url.split('//')[1].split('/')[0].split(':')[0]
        sub_link = f"https://{base_host}/egcPsGWuDm/{sub.email}"
        
        text += f"🔑 **Активная подписка**\n"
        text += f"📅 Истекает: {expiry} ({days_left} дн.)\n"
        text += f"🌍 Сервер: {sub.server.location}\n"
        
        # Add Buttons
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📥 Моя подписка", url=sub_link))
        builder.row(InlineKeyboardButton(text="🔑 Посмотреть мой ключ", callback_data="view_key"))
        builder.row(InlineKeyboardButton(text="👥 Пригласить друга", callback_data="ref_link"))
        markup = builder.as_markup()
    else:
        text += "❌ Нет активной подписки."
        # Add Ref Button even if no sub
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="👥 Пригласить друга", callback_data="ref_link"))
        markup = builder.as_markup()
        
    await message.answer(text, reply_markup=markup, parse_mode="Markdown")

@router.callback_query(F.data == "ref_link")
async def show_ref_link(callback: CallbackQuery):
    link = f"https://t.me/{BOT_USERNAME}?start={callback.from_user.id}"
    await callback.message.answer(f"🔗 **Ваша реферальная ссылка:**\n`{link}`\n\nПригласите друга и получите 7 дней подписки бесплатно!", parse_mode="Markdown")
    await callback.answer()

@router.message(F.text == '💳 Купить подписку')
async def buy_subscription(message: Message):
    from sqlalchemy import select
    async with rq.async_session() as session:
        plans = (await session.scalars(select(Plan).where(Plan.price > 0).order_by(Plan.price))).all()
    
    await message.answer("Выберите тариф:", reply_markup=await inline_plans(plans))

@router.callback_query(F.data.startswith("buy_plan_"))
async def process_buy_plan(callback: CallbackQuery, bot: Bot):
    import json
    plan_id = int(callback.data.split("_")[2])
    
    user = await rq.select_user(callback.from_user.id)
    async with rq.async_session() as session:
        plan = await session.get(Plan, plan_id)
    
    if not plan:
        await callback.answer("Тариф не найден.", show_alert=True)
        return

    # 1. Full Balance Check
    if user.balance >= plan.price:
        await rq.deduct_balance(user.tg_id, plan.price)
        server = await rq.get_active_server()
        if server:
            success = await issue_subscription(user.tg_id, plan, server, bot)
            if success:
                await callback.answer("✅ Подписка оплачена с баланса!", show_alert=True)
            else:
                await callback.message.answer("⚠️ Ошибка при активации. Деньги списаны, обратитесь в поддержку.")
        return

    # 2. Hybrid Payment: Pay the difference
    amount_to_pay = plan.price - user.balance
    
    # Receipt data for YooKassa (Fiscalization)
    receipt_data = {
        "receipt": {
            "items": [
                {
                    "description": f"VPN: {plan.name} (доплата)",
                    "quantity": 1,
                    "amount": {
                        "value": str(amount_to_pay),
                        "currency": "RUB"
                    },
                    "vat_code": 1,
                    "payment_mode": "full_payment",
                    "payment_subject": "service"
                }
            ],
            "tax_system_code": 1
        }
    }

    try:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"Подписка {plan.name}",
            description=f"Доплата за VPN. Использовано с баланса: {user.balance} RUB. К оплате: {amount_to_pay} RUB.",
            payload=f"vpn_payment:{plan.id}:{callback.from_user.id}:{user.balance}", # payload includes balance used
            provider_token=os.getenv("YOOKASSA_LIVE_TOKEN"),
            currency="RUB",
            prices=[LabeledPrice(label=f"Доплата за {plan.name}", amount=int(amount_to_pay * 100))],
            start_parameter="create_invoice_vpn_sub",
            is_flexible=False,
            need_email=True,
            send_email_to_provider=True,
            provider_data=json.dumps(receipt_data)
        )
    except Exception as e:
        await callback.answer(f"⚠️ Ошибка при создании платежа: {str(e)}", show_alert=True)
        return

    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout_query(pre_checkout_q: PreCheckoutQuery, bot: Bot):
    print(f"DEBUG: Received pre_checkout_query: {pre_checkout_q.id}")
    try:
        await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)
        print("DEBUG: Answered pre_checkout_query: OK")
    except Exception as e:
        print(f"DEBUG: Failed to answer pre_checkout_query: {e}")

@router.message(F.successful_payment)
async def successful_payment(message: Message, bot: Bot):
    payload = message.successful_payment.invoice_payload
    parts = payload.split(":")
    
    plan_id = int(parts[1])
    tg_id = int(parts[2])
    balance_used = float(parts[3]) if len(parts) > 3 else 0

    # 1. Deduct balance that was applied as discount
    if balance_used > 0:
        await rq.deduct_balance(tg_id, balance_used)

    # 2. Activate Subscription
    server = await rq.get_active_server()
    async with rq.async_session() as session:
        plan = await session.get(Plan, plan_id)
    
    if server and plan:
        success = await issue_subscription(tg_id, plan, server, bot)
        if success:
             return

    await message.answer("✅ Оплата прошла, но возникла ошибка при создании ключа. Обратитесь в поддержку.")

    
    await message.answer("✅ Оплата прошла, но возникла ошибка при создании ключа. Обратитесь в поддержку.")

@router.callback_query(F.data == "view_key")
async def view_key(callback: CallbackQuery):
    sub = await rq.get_user_subscription(callback.from_user.id)
    if sub:
        msg = f"🔑 **Ваш ключ:**\n`{sub.key_url}`\n\n👆 Нажмите на текст ключа, чтобы скопировать его."
        await callback.message.answer(msg, parse_mode="Markdown")
        await callback.answer()
    else:
        await callback.answer("Подписка не найдена.", show_alert=True)

@router.callback_query(F.data == "copy_instruction")
async def copy_instruction(callback: CallbackQuery):
    await callback.answer("👆 Нажмите на текст ключа, чтобы скопировать его.", show_alert=True)

@router.message(F.text == '🆘 Поддержка')
async def support(message: Message):
    await message.answer("По всем вопросам пишите: @berdanckin") # Replace with real support
