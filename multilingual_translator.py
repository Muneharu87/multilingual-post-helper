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




def translate_message(text):
    """
    langdetectで入力テキストの言語を自動検出
    -> その他の2言語に翻訳し、結果を辞書として返します。
    """
    if not text.strip():
        return None, None

    try:
        # 1. 入力言語の検出 (langdetect を使用)
        detected_lang = langdetect_detect(text)

        # 検出された言語コードがサポート対象か確認
        if detected_lang not in TARGET_LANGUAGES:
            # ★★★ 誤検出（koなど）が発生した場合のフォールバック処理 ★★★
            # langdetect が失敗しても、GoogleTranslator の 'auto' 検出に処理を任せる
            # この場合、検出言語は「不明(auto)」として処理を続行する

            # GoogleTranslatorのauto検出に任せるため、ソース言語を 'auto' に設定
            source_for_translator = 'auto'
            # 検出された言語の表示は '不明' にしておく
            detected_lang = 'auto'

        else:
            # サポート対象の言語が検出された場合
            source_for_translator = TRANSLATOR_TARGETS.get(detected_lang, detected_lang)

        # 2. 翻訳ペアの決定と翻訳の実行
        translation_results = {}
        all_codes = TARGET_LANGUAGES.keys()

        # 3. 各言語への翻訳を実行 (原文を含む)
        for target_code in all_codes:
            # 簡体字/繁体字で翻訳エンジンが使うコードを取得
            target_for_translator = TRANSLATOR_TARGETS[target_code]

            # 検出言語が 'auto' の場合、常に翻訳処理を行う
            if detected_lang != 'auto' and target_code == detected_lang:
                # 原文はそのまま (langdetectで確実に検出できた場合のみ)
                translation_results[target_code] = text
            else:
                # source と target を動的に設定して翻訳
                current_translator = GoogleTranslator(
                    source=source_for_translator,  # 'auto' または 'zh-CN', 'ja', 'vi'
                    target=target_for_translator
                )

                translated_text = current_translator.translate(text)

                # 'auto'検出で翻訳した場合、検出言語を確定させる
                if detected_lang == 'auto' and target_code == 'ja':
                    # 'ja'への翻訳で使われた元の言語コードをGoogleTranslatorから取得（ただし、これは厳密には困難なため、シンプルに処理を続ける）
                    pass

                translation_results[target_code] = translated_text

        # フォールバック（'auto'）で処理した場合、検出言語の表示を調整
        if detected_lang == 'auto':
            # 翻訳成功とみなし、ユーザーが入力した原文を ja, zh, vi のいずれか（ここでは ja を仮定）として扱う
            # ただし、元の入力が中国語なので、ここで detected_lang を 'zh' に上書きするのが最善です
            detected_lang_display = 'zh'
        else:
            detected_lang_display = detected_lang

        # 翻訳結果の辞書と、検出された言語コードを返します
        return translation_results, detected_lang_display

    except LangDetectException:
        # 従来通り、短いテキストなどのエラーを処理
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