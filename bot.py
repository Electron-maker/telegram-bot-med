# Простой и удобный Telegram-бот для учеников

from aiogram import Bot, Dispatcher, types
from aiogram.types import InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher.filters import CommandStart
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
import logging
import os

API_TOKEN = 'YOUR_BOT_TOKEN'
ADMIN_ID = YOUR_ADMIN_ID  # например: 6449574815
CARD_PATH = 'cards'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

class Form(StatesGroup):
    subjects = State()
    months = State()
    waiting_for_receipt = State()

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
    await state.update_data(subjects=[], months=1)
    await state.set_state(Form.subjects.state)

    image = InputFile(os.path.join(CARD_PATH, 'combined.jpg'))
    keyboard = InlineKeyboardMarkup(row_width=2)
    for subject in subjects_data:
        emoji = subjects_emojis[subject]
        keyboard.insert(InlineKeyboardButton(f"{emoji} {subject}", callback_data=f"choose_{subject}"))
    keyboard.add(InlineKeyboardButton("✅ Далее", callback_data="continue"))

    await message.answer_photo(photo=image, caption="Привет! Выбери предметы для изучения:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith('choose_'), state=Form.subjects)
async def choose_subject(callback_query: types.CallbackQuery, state: FSMContext):
    subject = callback_query.data.split('_')[1]
    data = await state.get_data()
    subjects = data.get("subjects", [])
    if subject not in subjects:
        subjects.append(subject)
        await state.update_data(subjects=subjects)
    await callback_query.answer(f"Вы выбрали: {subject}")

@dp.callback_query_handler(lambda c: c.data == 'continue', state=Form.subjects)
async def process_continue(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    subjects = data.get("subjects", [])
    if not subjects:
        await callback_query.answer("Выберите хотя бы один предмет!", show_alert=True)
        return
    await Form.next()
    await callback_query.message.delete()
    months_keyboard = InlineKeyboardMarkup(row_width=4)
    for i in range(1, 13):
        months_keyboard.insert(InlineKeyboardButton(str(i), callback_data=f"months_{i}"))
    await bot.send_message(callback_query.from_user.id, "На сколько месяцев оплатить курс?", reply_markup=months_keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith('months_'), state=Form.months)
async def process_months(callback_query: types.CallbackQuery, state: FSMContext):
    months = int(callback_query.data.split('_')[1])
    data = await state.get_data()
    subjects = data.get("subjects", [])
    await state.update_data(months=months)

    price_per_subject = 250
    total = price_per_subject * len(subjects) * months
    discount = 0.05 if 3 <= months <= 5 else 0.08 if 6 <= months <= 11 else 0.10 if months == 12 else 0.0
    discounted_total = int(total * (1 - discount))

    text = (
        f"📚 Предметы: {', '.join(subjects)}\n"
        f"📅 Месяцев: {months}\n"
        f"💰 Цена: {total} сомони\n"
        f"🔻 Скидка: {int(discount * 100)}%\n"
        f"💳 К оплате: {discounted_total} сомони\n\n"
        f"Оплатите на карту: 992558010200 (Курбонзода М.М)\n"
        f"После оплаты нажмите кнопку ниже и отправьте фото чека."
    )

    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("📤 Я оплатил", callback_data="paid")
    )
    await callback_query.message.delete()
    await bot.send_message(callback_query.from_user.id, text, reply_markup=keyboard)
    await Form.waiting_for_receipt.set()

@dp.callback_query_handler(lambda c: c.data == 'paid', state=Form.waiting_for_receipt)
async def ask_receipt(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.delete()
    await bot.send_message(callback_query.from_user.id, "📸 Пришлите фото чека.")

@dp.message_handler(content_types=types.ContentType.PHOTO, state=Form.waiting_for_receipt)
async def handle_receipt(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    subjects = data.get("subjects", [])
    months = data.get("months", 1)

    photo = message.photo[-1]
    caption = (
        f"🧾 Новый чек от @{message.from_user.username or 'Без ника'}\n"
        f"Предметы: {', '.join(subjects)}\n"
        f"Месяцев: {months}"
    )
    await bot.send_photo(chat_id=ADMIN_ID, photo=photo.file_id, caption=caption)

    final_msg = (
        "✅ Спасибо! Ваш чек отправлен.\n"
        "Мы проверим оплату и добавим вас в закрытую группу.\n"
        "Если не добавили в течение 30 минут — напишите нам."
    )

    keyboard = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("🔁 Начать сначала", callback_data="main_menu"),
        InlineKeyboardButton("💬 Поддержка", url="https://t.me/Duolingocoin")
    )

    await message.answer(final_msg, reply_markup=keyboard)
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'main_menu')
async def return_to_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.delete()
    await start(callback_query.message, state)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
