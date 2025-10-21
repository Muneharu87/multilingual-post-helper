# multilingual_translator.py (LINE/トーク投稿支援ツール版)

from flask import Flask, render_template, request
from deep_translator import GoogleTranslator
from langdetect import detect as langdetect_detect
from langdetect.lang_detect_exception import LangDetectException


# Flaskアプリケーションを初期化
app = Flask(__name__) # このあたりにあります

# 使用する言語コードを定義 (langdetect の出力と deep-translator の入力に合わせます)
TARGET_LANGUAGES = {  # ★この行のスペルが間違っていないか確認！
    'ja': '🇯🇵 日本語',
    'zh': '🇨🇳 中国語',      # langdetect の出力 (簡体字)
    'zh-cn': '🇨🇳 中国語',   # langdetect が返す可能性のあるコード
    'vi': '🇻🇳 ベトナム語'
}
# 翻訳エンジンが使うターゲット言語コードのマップ
TRANSLATOR_TARGETS = {  # ★この行のスペルが間違っていないか確認！
    'ja': 'ja',
    'zh': 'zh-CN',
    'zh-cn': 'zh-CN',
    'vi': 'vi'
}

# ... (続くコード)


def translate_message(text):
    """
    langdetectで入力テキストの言語を自動検出
    -> その他の2言語に翻訳し、結果を辞書として返します。
    """
    if not text.strip():
        return None, None

    try:
        # 1. 入力言語の検出 (langdetect を使用)
        # GoogleTranslator は detect メソッドを持たないので、langdetect を使用します
        detected_lang = langdetect_detect(text)

        # 検出された言語コードがサポート対象か確認
        if detected_lang not in TARGET_LANGUAGES:
            return None, f"エラー: 検出された言語({detected_lang})はサポートされていません。"

        # 2. 翻訳ペアの決定と翻訳の実行
        translation_results = {}  # 翻訳結果の辞書を初期化

        # 翻訳ターゲット言語のリストを作成（すべてのサポート言語）
        all_codes = TARGET_LANGUAGES.keys()

        # 3. 各言語への翻訳を実行 (原文を含む)
        for target_code in all_codes:
            if target_code == detected_lang:
                # 原文はそのまま
                translation_results[target_code] = text
            else:
                # deep-translator が求める言語コードに変換
                source_for_translator = TRANSLATOR_TARGETS.get(detected_lang, detected_lang)
                target_for_translator = TRANSLATOR_TARGETS[target_code]

                # source と target を動的に設定して翻訳
                current_translator = GoogleTranslator(
                    source=source_for_translator,
                    target=target_for_translator
                )

                translated_text = current_translator.translate(text)
                translation_results[target_code] = translated_text

        # 翻訳結果の辞書と、検出された言語コードを返します
        return translation_results, detected_lang

    except LangDetectException:
        return None, "エラー: テキストが短すぎる、または言語を検出できませんでした。"
    except Exception as e:
        print(f"翻訳中に予期せぬエラーが発生しました: {e}")
        return None, f"翻訳エラーが発生しました: {e}"


# ウェブサイトのトップページ (ルート /) の処理
@app.route('/', methods=['GET', 'POST'])
def index():
    translation_results = None
    original_text = None
    detected_lang = None
    error_message = None
    full_output = ""  # ★新規: コピー用テキストを格納する変数

    if request.method == 'POST':
        input_text = request.form.get('input_text')  # HTMLの入力欄の名前を変更します

        if input_text and input_text.strip():
            translation_results, detected_lang = translate_message(input_text)
            original_text = input_text  # 再表示のために元のテキストを保持

            if isinstance(detected_lang, str) and detected_lang.startswith("エラー:"):
                error_message = detected_lang
            elif translation_results:
                # ★新規: コピー用テキストを作成
                output_lines = []
                for lang_code in ['ja', 'zh', 'vi']:  # 順番を固定
                    if lang_code in translation_results:
                        lang_label = f"{TARGET_LANGUAGES[lang_code]}:"
                        # 原文はラベルを「(原文)」のように修正
                        if lang_code == detected_lang:
                            lang_label = f"{TARGET_LANGUAGES[lang_code]} (原文):"

                        output_lines.append(f"{lang_label}\n{translation_results[lang_code]}")

                # 改行で区切られた一つの文字列として保存
                full_output = "\n\n".join(output_lines)

    # HTMLテンプレート (templates/index.html) を表示する
    return render_template(
        'index.html',
        results=translation_results,
        original_text=original_text,
        all_langs=TARGET_LANGUAGES,
        detected_lang_code=detected_lang,
        error=error_message,
        full_output=full_output  # ★新規: コピー用テキストを渡します
    )


if __name__ == '__main__':
    # 開発用サーバーを起動
    app.run(debug=True)