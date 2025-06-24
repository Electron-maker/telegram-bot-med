from aiogram import Bot, Dispatcher, types
from aiogram.types import InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher.filters import CommandStart
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
import logging
import os

API_TOKEN = '8063346130:AAGcwNNQXzNZjaE3Nes4eKmiQr2FRAvdgc4'  # <-- Замените на свой
ADMIN_ID = 6449574815  # <-- Замените на свой

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

class Form(StatesGroup):
    subjects = State()
    months = State()
    waiting_for_receipt = State()

CARD_PATH = 'cards'
user_data = {}

subjects_data = {
    'Химия': 'chemistry.jpg',
    'Физика': 'physics.jpg',
    'Биология': 'biology.jpg',
    'Математика': 'math.jpg'
}

subjects_emojis = {
    'Химия': '🔬',
    'Физика': '⚛️',
    'Биология': '🧬',
    'Математика': '➗'
}

@dp.message_handler(CommandStart())
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_data[user_id] = {'subjects': [], 'months': 1}
    await state.set_state(Form.subjects.state)

    image = InputFile(os.path.join(CARD_PATH, 'combined.jpg'))
    keyboard = InlineKeyboardMarkup(row_width=2)
    for subject in subjects_data:
        emoji = subjects_emojis[subject]
        keyboard.insert(InlineKeyboardButton(f"{emoji} {subject}", callback_data=f"choose_{subject}"))
    keyboard.add(InlineKeyboardButton("✅ Продолжить", callback_data="continue"))

    await message.answer_photo(photo=image, caption="Добро пожаловать! Ниже выберите предметы, которые хотите изучать:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith('choose_'), state=Form.subjects)
async def choose_subject(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {'subjects': [], 'months': 1}
    subject = callback_query.data.split('_')[1]
    if subject not in user_data[user_id]['subjects']:
        user_data[user_id]['subjects'].append(subject)
    await callback_query.answer(f"Вы выбрали: {subject}")

@dp.callback_query_handler(lambda c: c.data == 'continue', state=Form.subjects)
async def process_continue(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    if user_id not in user_data or not user_data[user_id]['subjects']:
        await callback_query.answer("Вы не выбрали ни одного предмета", show_alert=True)
        return
    await Form.next()
    await callback_query.message.delete()
    months_keyboard = InlineKeyboardMarkup(row_width=4)
    for i in range(1, 13):
        months_keyboard.insert(InlineKeyboardButton(str(i), callback_data=f"months_{i}"))
    await bot.send_message(user_id, "На сколько месяцев вы хотите оплатить курс?", reply_markup=months_keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith('months_'), state=Form.months)
async def process_months(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    months = int(callback_query.data.split('_')[1])
    user_data[user_id]['months'] = months

    price_per_subject = 250
    num_subjects = len(user_data[user_id]['subjects'])
    total = price_per_subject * num_subjects * months

    if 3 <= months <= 5:
        discount = 0.05
    elif 6 <= months <= 11:
        discount = 0.08
    elif months == 12:
        discount = 0.10
    else:
        discount = 0.0

    discounted_total = int(total * (1 - discount))

    message_text = (
        f"Предметы: {', '.join(user_data[user_id]['subjects'])}\n"
        f"Месяцев: {months}\n"
        f"Цена до скидки: {total} сомони\n"
        f"Скидка: {int(discount * 100)}%\n"
        f"Итоговая сумма: {discounted_total} сомони\n\n"
        f"💳 Пожалуйста, оплатите на следующие реквизиты:\n"
        f"Карта: 992558010200\n"
        f"Имя получателя: Курбонзода М.М\n\n"
        f"После оплаты нажмите кнопку ниже и загрузите чек."
    )

    pay_button = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Я оплатил", callback_data="paid")
    )
    await callback_query.message.delete()
    await bot.send_message(user_id, message_text, reply_markup=pay_button)
    await Form.waiting_for_receipt.set()

@dp.callback_query_handler(lambda c: c.data == 'paid', state=Form.waiting_for_receipt)
async def ask_receipt(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.delete()
    await bot.send_message(callback_query.from_user.id, "Пожалуйста, загрузите фото чека.")

@dp.message_handler(content_types=types.ContentType.PHOTO, state=Form.waiting_for_receipt)
async def handle_receipt(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in user_data:
        await message.answer("Сначала начните с команды /start.")
        return
    photo = message.photo[-1]
    caption = (
        f"📥 Новый чек от пользователя @{message.from_user.username or 'Без ника'}\n"
        f"Предметы: {', '.join(user_data[user_id]['subjects'])}\n"
        f"Месяцев: {user_data[user_id]['months']}"
    )
    await bot.send_photo(chat_id=ADMIN_ID, photo=photo.file_id, caption=caption)

    final_msg = (
        "✅ Спасибо, что выбрали наш образовательный проект!\n\n"
        "Ваш платёж сейчас проверяется администратором.\n"
        "⏳ Это может занять немного времени из-за загруженности.\n"
        "Если в течение 30 минут вас не добавили в закрытую группу или с вами не связались,\n"
        "свяжитесь с нами:\n"
        "📩 Telegram: @Duolingocoin\n"
        "📞 Телефон: +992 98 444 74 00"
    )

    menu_keyboard = InlineKeyboardMarkup(row_width=2)
    menu_keyboard.add(
        InlineKeyboardButton("🔁 В начало", callback_data="main_menu"),
        InlineKeyboardButton("📞 Поддержка", url="https://t.me/Duolingocoin")
    )

    await message.answer(final_msg, parse_mode="Markdown", reply_markup=menu_keyboard)
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'main_menu')
async def return_to_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.delete()
    await start(callback_query.message, state)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
