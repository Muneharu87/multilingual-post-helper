# multilingual_translator.py (DeepL対応版)

from flask import Flask, render_template, request
from langdetect import detect as langdetect_detect
from langdetect.lang_detect_exception import LangDetectException
import os
import deepl  # ★ DeepLをインポート

# Flaskアプリケーションを初期化
app = Flask(__name__)

# ★ DeepL APIキーを環境変数から取得します ★
# ローカルでテストする場合は os.environ.get('DEEPL_AUTH_KEY', 'YOUR_API_KEY_HERE') のように
# 直接キーを記述しても動作しますが、デプロイ時は環境変数を使ってください。
# Renderで設定する方法は後述します。
DEEPL_AUTH_KEY = os.environ.get('DEEPL_AUTH_KEY')
if not DEEPL_AUTH_KEY:
    # 実際にはRenderの環境変数で設定するため、この警告はローカルテスト用です。
    print("警告: DEEPL_AUTH_KEYが環境変数に設定されていません。")

# 使用する言語コードを定義 (langdetect/DeepLの入力に合わせます)
TARGET_LANGUAGES = {
    'ja': '🇯🇵 日本語',
    'zh': '🇨🇳 中国語',
    'vi': '🇻🇳 ベトナム語'
}

# DeepLが使うターゲット言語コードのマップ
# DeepLはより標準的なコードを使います (簡体字は 'zh')
DEEPL_TARGETS = {
    'ja': 'JA',
    'zh': 'ZH',  # DeepLの中国語コードは 'ZH'
    'vi': 'VI'
}

# 翻訳エンジンの初期化
try:
    translator = deepl.Translator(DEEPL_AUTH_KEY)
except Exception as e:
    # APIキーが無効な場合など、初期化に失敗した場合の処理
    print(f"DeepL翻訳クライアントの初期化に失敗しました: {e}")
    translator = None


def translate_message(text):
    """
    langdetectで入力テキストの言語を自動検出
    -> その他の2言語に翻訳し、結果を辞書として返します。
    """
    global translator

    if not text.strip() or translator is None:
        return None, "翻訳エンジンが正しく初期化されていません。"

    try:
        # 1. 入力言語の検出 (langdetect を使用)
        detected_lang = langdetect_detect(text)

        # 検出された言語コードがサポート対象か確認 (zh-cnはzhに変換して処理)
        detected_lang_base = 'zh' if detected_lang in ['zh', 'zh-cn'] else detected_lang

        # 2. 翻訳ペアの決定と翻訳の実行
        translation_results = {}
        all_codes = TARGET_LANGUAGES.keys()

        # 3. 各言語への翻訳を実行 (原文を含む)
        for target_code in all_codes:

            # DeepLのターゲットコードを取得
            target_for_deepl = DEEPL_TARGETS[target_code]

            if target_code == detected_lang_base:
                # 原文はそのまま
                translation_results[target_code] = text
            else:
                # DeepLのソースコードを取得 (langdetectの出力に合わせる)
                source_for_deepl = detected_lang_base.upper()

                # DeepL APIを使って翻訳
                result = translator.translate_text(
                    text,
                    source_lang=source_for_deepl,
                    target_lang=target_for_deepl
                )
                translated_text = result.text
                translation_results[target_code] = translated_text

        return translation_results, detected_lang_base

    except LangDetectException:
        return None, "エラー: テキストが短すぎる、または言語を検出できませんでした。"
    except deepl.exceptions.DeepLException as e:
        return None, f"DeepL翻訳エラーが発生しました。APIキーを確認してください: {e}"
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
        return None, f"翻訳エラーが発生しました: {e}"


# ウェブサイトのトップページ (ルート /) の処理（変更なし）
@app.route('/', methods=['GET', 'POST'])
def index():
    translation_results = None
    original_text = None
    detected_lang = None
    error_message = None
    full_output = ""

    # DeepLクライアントが初期化されていない場合はエラーとする
    if translator is None:
        error_message = "致命的なエラー：DeepL翻訳クライアントが初期化できませんでした。APIキーを確認してください。"
        return render_template(
            'index.html',
            results=None,
            original_text=None,
            all_langs=TARGET_LANGUAGES,
            detected_lang_code=None,
            error=error_message,
            full_output=""
        )

    if request.method == 'POST':
        input_text = request.form.get('input_text')

        if input_text and input_text.strip():
            translation_results, detected_lang = translate_message(input_text)
            original_text = input_text

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
        full_output=full_output
    )


if __name__ == '__main__':
    # 開発用サーバーを起動 (DeepLを使う場合は、ローカル環境でもDEEPL_AUTH_KEYを設定する必要があります)
    # 例: export DEEPL_AUTH_KEY='YOUR_KEY'
    app.run(debug=True)