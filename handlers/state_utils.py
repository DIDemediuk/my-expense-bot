# handlers/state_utils.py

from telegram.ext import ConversationHandler, ContextTypes
from telegram import Update
from handlers.utils import send_main_menu
import logging

async def handle_back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ⬅️ Обробник кнопки 'Назад' та скидання стану. 
    Перериває поточну розмову та повертає користувача до головного меню.
    """
    query = update.callback_query
    
    # Обробка CallbackQuery
    if query:
        await query.answer()
        # Намагаємось видалити inline-меню, щоб воно не залишалося висіти
        try:
            await query.message.delete()
        except Exception as e:
            logging.debug(f"Не вдалося видалити повідомлення inline-меню: {e}")
            
    # Очищуємо дані користувача для початку нової розмови
    context.user_data.clear()
    
    # Надсилаємо головне меню
    # send_main_menu знаходиться у handlers/utils.py
    await send_main_menu(update, context, text="🔹 Меню закрито. Оберіть дію нижче.")
    return ConversationHandler.END