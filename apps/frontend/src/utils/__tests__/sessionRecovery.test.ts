import { afterEach, describe, expect, it } from 'vitest';
import {
  captureSessionRecovery,
  restoreSessionRecovery,
} from '../sessionRecovery';

describe('session input recovery', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    sessionStorage.clear();
  });

  it('restores same-tab form and chat input while excluding passwords', () => {
    document.body.innerHTML = `
      <form>
        <input value="recipe title" />
        <input type="password" value="not saved" />
        <textarea id="assistant-message">unsent chat</textarea>
      </form>
    `;
    const form = document.querySelector('form')!;
    const [title, password] = form.querySelectorAll('input');
    const message = form.querySelector('textarea')!;
    title.value = 'Recipe in progress';
    password.value = 'private';
    message.value = 'What can I substitute?';
    const changes: string[] = [];
    title.addEventListener('input', () => changes.push('title'));
    message.addEventListener('input', () => changes.push('message'));

    captureSessionRecovery();
    title.value = '';
    password.value = '';
    message.value = '';
    restoreSessionRecovery(window.location.pathname + window.location.search);

    expect(title.value).toBe('Recipe in progress');
    expect(message.value).toBe('What can I substitute?');
    expect(password.value).toBe('');
    expect(changes).toEqual(['title', 'message']);
    expect(sessionStorage.length).toBe(0);
  });

  it('does not restore another account’s saved inputs', () => {
    document.body.innerHTML = '<form><input value="Account A recipe"></form>';
    const input = document.querySelector('input')!;
    captureSessionRecovery('account-a');
    input.value = '';
    const path = window.location.pathname + window.location.search;

    restoreSessionRecovery(path, 'account-b');
    expect(input.value).toBe('');

    restoreSessionRecovery(path, 'account-a');
    expect(input.value).toBe('Account A recipe');
  });
});
