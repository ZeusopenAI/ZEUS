package com.zeus.keyboard;

import android.content.SharedPreferences;
import android.inputmethodservice.InputMethodService;
import android.inputmethodservice.Keyboard;
import android.inputmethodservice.KeyboardView;
import android.os.Build;
import android.text.InputType;
import android.view.KeyEvent;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;

import com.zeus.keyboard.ai.ZeusAIAssistant;
import com.zeus.keyboard.ui.VietnameseProcessor;

/**
 * Zeus AI Keyboard - Input Method Service
 * Bàn phím AI thông minh với hỗ trợ tiếng Việt và tích hợp AI.
 */
public class ZeusKeyboardService extends InputMethodService
        implements KeyboardView.OnKeyboardActionListener {

    private KeyboardView mKeyboardView;
    private Keyboard mMainKeyboard;
    private Keyboard mSymbolsKeyboard;
    private ZeusAIAssistant mAIAssistant;
    private VietnameseProcessor mVNProcessor;
    private boolean mIsShifted = false;
    private boolean mIsSymbols = false;
    private boolean mTelexEnabled = true;
    private StringBuilder mComposingBuffer = new StringBuilder();

    @Override
    public View onCreateInputView() {
        // KeyboardView không có constructor 1 tham số -> inflate từ XML.
        // Màu phím (keyBackground/keyTextColor) chỉ đặt được qua style XML,
        // xem res/values/styles.xml + res/layout/keyboard_view.xml.
        mKeyboardView = (KeyboardView) getLayoutInflater().inflate(R.layout.keyboard_view, null);
        mMainKeyboard = new Keyboard(this, R.xml.keyboard_main);
        mSymbolsKeyboard = new Keyboard(this, R.xml.keyboard_symbols);

        mKeyboardView.setKeyboard(mMainKeyboard);
        mKeyboardView.setOnKeyboardActionListener(this);
        mKeyboardView.setBackgroundColor(0xFF1A1A2E); // Dark navy background

        // Initialize AI
        mAIAssistant = new ZeusAIAssistant(this);
        mVNProcessor = new VietnameseProcessor();

        loadPreferences();
        return mKeyboardView;
    }

    private void loadPreferences() {
        SharedPreferences prefs = getSharedPreferences("zeus_keyboard_prefs", MODE_PRIVATE);
        mTelexEnabled = prefs.getBoolean("telex_enabled", true);
    }

    @Override
    public void onKey(int primaryCode, int[] keyCodes) {
        InputConnection ic = getCurrentInputConnection();
        if (ic == null) return;

        switch (primaryCode) {
            case Keyboard.KEYCODE_DELETE:
                handleBackspace(ic);
                break;

            case Keyboard.KEYCODE_SHIFT:
                handleShift();
                break;

            case Keyboard.KEYCODE_DONE:
                handleDone(ic);
                break;

            case Keyboard.KEYCODE_MODE_CHANGE:
                handleModeChange();
                break;

            case -10: // AI Button
                handleAIButton(ic);
                break;

            default:
                handleCharacter(primaryCode, ic);
                break;
        }
    }

    private void handleCharacter(int code, InputConnection ic) {
        if (mIsShifted) {
            code = Character.toUpperCase(code);
        }

        // Vietnamese Telex processing
        if (mTelexEnabled) {
            mComposingBuffer.append((char) code);
            String processed = mVNProcessor.processTelex(mComposingBuffer.toString());
            ic.setComposingText(processed, 1);
            mComposingBuffer = new StringBuilder(processed);

            // Auto-commit if the word looks complete
            if (shouldCommit()) {
                ic.finishComposingText();
                mComposingBuffer.setLength(0);
            }
        } else {
            ic.commitText(String.valueOf((char) code), 1);
        }

        // Auto-lowercase after one character.
        // `Keyboard` không có isSticky(); shift một lần là quay về lowercase.
        if (mIsShifted) {
            mIsShifted = false;
            updateShiftState();
        }
    }

    private void handleBackspace(InputConnection ic) {
        if (mComposingBuffer.length() > 0) {
            mComposingBuffer.deleteCharAt(mComposingBuffer.length() - 1);
            if (mComposingBuffer.length() == 0) {
                ic.commitText("", 0);
            } else {
                String processed = mVNProcessor.processTelex(mComposingBuffer.toString());
                ic.setComposingText(processed, 1);
                mComposingBuffer = new StringBuilder(processed);
            }
        } else {
            ic.deleteSurroundingText(1, 0);
        }
    }

    private void handleShift() {
        mIsShifted = !mIsShifted;
        updateShiftState();
    }

    private void handleDone(InputConnection ic) {
        // Commit any composing text
        if (mComposingBuffer.length() > 0) {
            ic.finishComposingText();
            mComposingBuffer.setLength(0);
        }

        EditorInfo editorInfo = getCurrentInputEditorInfo();
        if (editorInfo != null) {
            int imeOptions = editorInfo.imeOptions;
            int actionId = imeOptions & EditorInfo.IME_MASK_ACTION;
            if (actionId != EditorInfo.IME_ACTION_NONE) {
                ic.performEditorAction(actionId);
            } else {
                ic.commitText("\n", 1);
            }
        } else {
            ic.commitText("\n", 1);
        }
    }

    private void handleModeChange() {
        if (mIsSymbols) {
            mKeyboardView.setKeyboard(mMainKeyboard);
            mIsSymbols = false;
        } else {
            mKeyboardView.setKeyboard(mSymbolsKeyboard);
            mIsSymbols = true;
        }
    }

    private void handleAIButton(InputConnection ic) {
        // Get current text context
        CharSequence beforeText = ic.getTextBeforeCursor(100, 0);
        String context = beforeText != null ? beforeText.toString() : "";

        // Commit composing text first
        if (mComposingBuffer.length() > 0) {
            ic.finishComposingText();
            mComposingBuffer.setLength(0);
        }

        // Send to AI and insert response
        mAIAssistant.quickComplete(context, response -> {
            if (response != null && !response.isEmpty()) {
                ic.commitText(response, 1);
            }
        });
    }

    private void updateShiftState() {
        if (mKeyboardView != null && mMainKeyboard != null) {
            mMainKeyboard.setShifted(mIsShifted);
            mKeyboardView.invalidateAllKeys();
        }
    }

    private boolean shouldCommit() {
        // Commit when buffer is long enough or contains completed Vietnamese
        return mComposingBuffer.length() > 30 ||
               mVNProcessor.isCompleteWord(mComposingBuffer.toString());
    }

    @Override
    public void onPress(int primaryCode) {
        // Visual feedback
    }

    @Override
    public void onRelease(int primaryCode) {
        // Visual feedback
    }

    @Override
    public void onText(CharSequence text) {
        InputConnection ic = getCurrentInputConnection();
        if (ic != null) {
            ic.commitText(text, 1);
        }
    }

    @Override
    public void swipeLeft() {}

    @Override
    public void swipeRight() {}

    @Override
    public void swipeDown() {
        // Hide keyboard
        requestHideSelf(0);
    }

    @Override
    public void swipeUp() {}
}
