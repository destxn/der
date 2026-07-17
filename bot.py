#!/usr/bin/env python3
"""
Telegram Alacak-Verecek Botu
Kullanım:
  /baslat @alacakli @borclu  -> yeni borç kaydı başlat
  Sayı yazmak                  -> alacaklı için borç tutarı, borçlu için ödeme
  /toplam                      -> kalan borcu göster
  /liste                       -> tüm aktif borçları listele
  /iptal                       -> aktif borç kaydını sil
"""

import os
import json
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ---------- Veritabanı (JSON dosyası) ----------
DB_FILE = "borclar.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------- Komutlar ----------

async def baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /baslat @alacakli @borclu
    Yeni bir borç kaydı başlatır.
    """
    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "❌ Kullanım: /baslat @alacakli @borclu\n"
            "Örnek: /baslat @destan @ahmet"
        )
        return

    alacakli = args[0].lstrip("@")
    borclu = args[1].lstrip("@")

    if alacakli == borclu:
        await update.message.reply_text("❌ Alacaklı ve borçlu aynı kişi olamaz!")
        return

    db = load_db()

    # Benzersiz ID
    kayit_id = f"{alacakli}_{borclu}"

    if kayit_id in db:
        await update.message.reply_text(
            f"⚠️ @{alacakli} ve @{borclu} arasında zaten aktif bir borç kaydı var.\n"
            f"Kalan borç: {db[kayit_id]['kalan']} TL"
        )
        return

    db[kayit_id] = {
        "alacakli": alacakli,
        "borclu": borclu,
        "toplam": 0,
        "kalan": 0,
        "odenen": 0,
        "durum": "miktar_bekleniyor",  # önce alacaklı toplam borcu girecek
    }
    save_db(db)

    await update.message.reply_text(
        f"✅ Yeni borç kaydı oluşturuldu!\n"
        f"💰 Alacaklı: @{alacakli}\n"
        f"🧾 Borçlu: @{borclu}\n\n"
        f"⚠️ Şimdi ALACAKLI kişi (@{alacakli}) toplam borç miktarını yazsın.\n"
        f"Örnek: 1000"
    )


async def toplam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /toplam -> tüm aktif borçları veya belirli bir kaydı gösterir
    """
    db = load_db()
    username = update.effective_user.username or update.effective_user.first_name

    if not db:
        await update.message.reply_text("📭 Hiç aktif borç kaydı yok.")
        return

    response = "📊 **Aktif Borç Kayıtları:**\n\n"

    # Kullanıcının dahil olduğu kayıtları filtrele (alacaklı veya borçlu olarak)
    found = False
    for kayit_id, borc in db.items():
        if borc["alacakli"] == username or borc["borclu"] == username:
            found = True
            response += (
                f"🔹 Alacaklı: @{borc['alacakli']}\n"
                f"   Borçlu: @{borc['borclu']}\n"
                f"   Toplam borç: {borc['toplam']} TL\n"
                f"   Ödenen: {borc['odenen']} TL\n"
                f"   ⚠️ Kalan borç: **{borc['kalan']} TL**\n"
                f"   Durum: {borc['durum']}\n\n"
            )

    if not found:
        await update.message.reply_text(
            "📭 Size ait aktif bir borç kaydı bulunamadı.\n"
            "Yeni kayıt için: /baslat @alacakli @borclu"
        )
        return

    await update.message.reply_text(response.strip(), parse_mode="Markdown")


async def liste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tüm borç kayıtlarını listeler (admin görünümü)"""
    db = load_db()

    if not db:
        await update.message.reply_text("📭 Hiç aktif borç kaydı yok.")
        return

    response = "📋 **Tüm Borç Kayıtları:**\n\n"
    for kayit_id, borc in db.items():
        response += (
            f"🆔 `{kayit_id}`\n"
            f"   Alacaklı: @{borc['alacakli']}\n"
            f"   Borçlu: @{borc['borclu']}\n"
            f"   Toplam: {borc['toplam']} TL | Kalan: {borc['kalan']} TL\n"
            f"   Durum: {borc['durum']}\n\n"
        )

    await update.message.reply_text(response.strip(), parse_mode="Markdown")


async def iptal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /iptal @alacakli @borclu -> belirli bir kaydı siler
    """
    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "❌ Kullanım: /iptal @alacakli @borclu\n"
            "Örnek: /iptal @destan @ahmet"
        )
        return

    alacakli = args[0].lstrip("@")
    borclu = args[1].lstrip("@")
    kayit_id = f"{alacakli}_{borclu}"

    db = load_db()
    if kayit_id not in db:
        await update.message.reply_text("❌ Böyle bir borç kaydı bulunamadı.")
        return

    del db[kayit_id]
    save_db(db)
    await update.message.reply_text(f"✅ @{alacakli} ↔ @{borclu} arasındaki borç kaydı silindi.")


async def mesaj_yakala(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sayısal mesajları yakala:
    - Eğer gönderen alacaklı ise ve kayıt "miktar_bekleniyor" durumundaysa → toplam borcu ayarla
    - Eğer gönderen borçlu ise ve kayıt "aktif" durumundaysa → ödeme olarak işle
    """
    text = update.message.text.strip()
    username = update.effective_user.username

    # Sayı mı kontrol et
    try:
        miktar = float(text)
    except ValueError:
        return  # sayı değilse görmezden gel

    if miktar <= 0:
        await update.message.reply_text("❌ Miktar pozitif bir sayı olmalıdır.")
        return

    db = load_db()

    # 1) ALACAKLI: "miktar_bekleniyor" durumundaki kaydı bul
    for kayit_id, borc in db.items():
        if borc["alacakli"] == username and borc["durum"] == "miktar_bekleniyor":
            borc["toplam"] = miktar
            borc["kalan"] = miktar
            borc["durum"] = "aktif"
            save_db(db)

            await update.message.reply_text(
                f"✅ Borç kaydı aktif edildi!\n\n"
                f"💰 Alacaklı: @{borc['alacakli']}\n"
                f"🧾 Borçlu: @{borc['borclu']}\n"
                f"💵 Toplam borç: {borc['toplam']} TL\n"
                f"⚠️ Kalan borç: **{borc['kalan']} TL**\n\n"
                f"📢 Borçlu @{borc['borclu']} ödeme yaptıkça miktarı buraya yazabilir.",
                parse_mode="Markdown",
            )
            return

    # 2) BORÇLU: "aktif" durumundaki kayda ödeme yap
    for kayit_id, borc in db.items():
        if borc["borclu"] == username and borc["durum"] == "aktif":
            if miktar > borc["kalan"]:
                await update.message.reply_text(
                    f"⚠️ Girdiğin miktar ({miktar} TL) kalan borçtan ({borc['kalan']} TL) fazla!\n"
                    f"Lütfen kalan borçtan az veya eşit bir miktar gir."
                )
                return

            borc["odenen"] += miktar
            borc["kalan"] -= miktar
            kalan = borc["kalan"]

            if kalan == 0:
                borc["durum"] = "tamamlandi"
                save_db(db)

                await update.message.reply_text(
                    f"🎉 **Borç tamamen ödendi!** 🎉\n\n"
                    f"💰 Alacaklı: @{borc['alacakli']}\n"
                    f"🧾 Borçlu: @{borc['borclu']}\n"
                    f"💵 Toplam borç: {borc['toplam']} TL\n"
                    f"✅ Ödenen: {borc['odenen']} TL\n"
                    f"🎯 Kalan borç: **0 TL**\n\n"
                    f"Tebrikler, borç kapandı! 👏",
                    parse_mode="Markdown",
                )

                # Alacaklıya da haber ver (eğer mümkünse aynı grupta)
                # Burada sadece mesajı atıyoruz, alacaklı aynı chat'te görecek
            else:
                save_db(db)

                await update.message.reply_text(
                    f"💸 Ödeme alındı: {miktar} TL\n\n"
                    f"💰 Alacaklı: @{borc['alacakli']}\n"
                    f"🧾 Borçlu: @{borc['borclu']}\n"
                    f"💵 Toplam borç: {borc['toplam']} TL\n"
                    f"✅ Toplam ödenen: {borc['odenen']} TL\n"
                    f"⚠️ **Kalan borç: {kalan} TL**",
                    parse_mode="Markdown",
                )
            return

    # Eğer kullanıcıya ait bekleyen/aktif kayıt yoksa
    await update.message.reply_text(
        f"ℹ️ @{username}, şu anda size ait işlenebilecek bir borç kaydı bulunamadı.\n"
        f"Yeni kayıt için: /baslat @alacakli @borclu"
    )


async def yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 **Alacak-Verecek Botu Komutları:**\n\n"
        "🔹 /baslat @alacakli @borclu → Yeni borç kaydı başlat\n"
        "🔹 Sayı yaz → Alacaklı: toplam borcu belirler / Borçlu: ödeme yapar\n"
        "🔹 /toplam → Kalan borcu gösterir\n"
        "🔹 /liste → Tüm borç kayıtlarını listeler\n"
        "🔹 /iptal @alacakli @borclu → Borç kaydını siler\n\n"
        "📝 **Kullanım örneği:**\n"
        "1. `/baslat @destan @ahmet`\n"
        "2. @destan toplam borcu yazar: `1000`\n"
        "3. @ahmet ödeme yaptıkça yazar: `500` → Kalan: 500 TL\n"
        "4. `/toplam` ile her an kalan borcu görebilirsiniz.",
        parse_mode="Markdown",
    )


# ---------- Ana Fonksiyon ----------

def main():
    TOKEN = os.environ.get("BOT_TOKEN", "BURAYA_BOT_TOKENİNİZİ_YAZIN")

    app = Application.builder().token(TOKEN).build()

    # Komutlar
    app.add_handler(CommandHandler("baslat", baslat))
    app.add_handler(CommandHandler("toplam", toplam))
    app.add_handler(CommandHandler("liste", liste))
    app.add_handler(CommandHandler("iptal", iptal))
    app.add_handler(CommandHandler("yardim", yardim))
    app.add_handler(CommandHandler("help", yardim))

    # Sayısal mesajları yakala (en sona ekle ki komutlar önce işlensin)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_yakala))

    print("🤖 Bot çalışıyor...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
