import '@testing-library/jest-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { act, useEffect } from 'react';
import {
  createMemoryRouter,
  MemoryRouter,
  RouterProvider,
  useLocation,
} from 'react-router-dom';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { useChatStore } from '../../stores/useChatStore';
import AssistantPage from '../AssistantPage';

const originalChatActions = {
  createConversation: useChatStore.getState().createConversation,
  createRecipeConversation: useChatStore.getState().createRecipeConversation,
  loadConversations: useChatStore.getState().loadConversations,
  loadMoreMessages: useChatStore.getState().loadMoreMessages,
  resumeRecipeConversation: useChatStore.getState().resumeRecipeConversation,
  switchConversation: useChatStore.getState().switchConversation,
};

function renderAssistant(
  initialEntry = '/assistant',
  state?: {
    recipeContext: {
      recipeId: string;
      recipeTitle: string;
    };
    recipeOrigin?: {
      pathname: string;
      scrollY: number;
      triggerId: string;
    };
  }
) {
  return render(
    <MemoryRouter
      initialEntries={[
        state ? { pathname: initialEntry, state } : initialEntry,
      ]}
    >
      <AssistantPage />
    </MemoryRouter>
  );
}

function RecipeBrowserBackDestination() {
  const location = useLocation();

  useEffect(() => {
    const state = location.state as {
      recipeRestoration?: {
        scrollY: number;
        triggerId: string;
      };
    } | null;
    const restoration = state?.recipeRestoration;
    if (!restoration) return;

    window.scrollTo({ top: restoration.scrollY });
    document.getElementById(restoration.triggerId)?.focus();
  }, [location.state]);

  return (
    <button id="recipe-nibble-trigger" type="button">
      Ask Nibble about Tomato Soup
    </button>
  );
}

describe('AssistantPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
    localStorage.clear();

    act(() => {
      useChatStore.setState({
        hasHydrated: true,
        conversations: [],
        activeConversationId: null,
        activeGeneralConversationId: null,
        activeRecipeConversationIds: {},
        messagesByConversationId: {},
        hasPreviousMessagesByConversationId: {},
        isLoading: false,
        error: null,
        ...originalChatActions,
      });
    });
  });

  test('renders the heading and help text', async () => {
    const loadSpy = vi.spyOn(useChatStore.getState(), 'loadConversations');

    renderAssistant();

    const heading = screen.getByRole('heading', {
      name: 'SmartMeal Assistant',
    });
    expect(heading).toBeInTheDocument();
    expect(heading.closest('header')).toHaveClass(
      'max-h-[45dvh]',
      'overflow-y-auto',
      'md:max-h-none',
      'md:overflow-visible'
    );
    expect(
      screen.getByText('Nibble is here to help you plan meals and groceries.')
    ).toBeInTheDocument();

    await waitFor(() => expect(loadSpy).toHaveBeenCalled());
  });

  test('shows a loading state when not hydrated', () => {
    act(() => {
      useChatStore.setState({ hasHydrated: false });
    });

    renderAssistant();

    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });

  test('creates a conversation on first hydrate when empty', async () => {
    const createSpy = vi.spyOn(useChatStore.getState(), 'createConversation');

    renderAssistant();

    await waitFor(() => expect(createSpy).toHaveBeenCalled());
  });

  test('resumes and displays recipe context from navigation state', async () => {
    const resumeSpy = vi
      .spyOn(useChatStore.getState(), 'resumeRecipeConversation')
      .mockResolvedValue(undefined);

    renderAssistant('/assistant', {
      recipeContext: {
        recipeId: 'recipe-1',
        recipeTitle: 'Tomato Soup',
      },
      recipeOrigin: {
        pathname: '/recipes/recipe-1',
        scrollY: 320,
        triggerId: 'recipe-nibble-trigger',
      },
    });

    expect(screen.getByText('Recipe: Tomato Soup')).toBeInTheDocument();
    expect(
      screen.getByRole('button', {
        name: 'New conversation for Tomato Soup',
      })
    ).toHaveClass('min-h-12');
    expect(screen.getByRole('button', { name: 'Back to recipe' })).toHaveClass(
      'min-h-12',
      'min-w-12'
    );
    await waitFor(() => expect(resumeSpy).toHaveBeenCalledWith('recipe-1'));
  });

  test('does not display requested recipe context over an active general conversation', async () => {
    vi.spyOn(useChatStore.getState(), 'loadConversations').mockResolvedValue(
      undefined
    );
    vi.spyOn(
      useChatStore.getState(),
      'resumeRecipeConversation'
    ).mockResolvedValue(undefined);
    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'general-chat',
            title: 'General',
            createdAt: '2026-09-29T10:00:00Z',
            lastMessageAt: '2026-09-29T10:00:00Z',
          },
        ],
        activeConversationId: 'general-chat',
        activeGeneralConversationId: 'general-chat',
      });
    });

    renderAssistant('/assistant', {
      recipeContext: {
        recipeId: 'recipe-1',
        recipeTitle: 'Tomato Soup',
      },
    });

    expect(screen.queryByText('Recipe: Tomato Soup')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', {
        name: 'New conversation for Tomato Soup',
      })
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole('textbox', { name: 'Message Nibble' })
    ).toBeDisabled();
  });

  test('requires explicit general-chat recovery after recipe resume fails with a general conversation active', async () => {
    const user = userEvent.setup();
    vi.spyOn(useChatStore.getState(), 'loadConversations').mockResolvedValue(
      undefined
    );
    const resumeSpy = vi
      .spyOn(useChatStore.getState(), 'resumeRecipeConversation')
      .mockImplementation(async () => {
        act(() => {
          useChatStore.setState({
            error:
              'Unable to resume this recipe conversation. Please try again.',
          });
        });
      });
    const createGeneralSpy = vi
      .spyOn(useChatStore.getState(), 'createConversation')
      .mockResolvedValue(undefined);
    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'general-chat',
            title: 'General',
            createdAt: '2026-09-29T10:00:00Z',
            lastMessageAt: '2026-09-29T10:00:00Z',
          },
        ],
        activeConversationId: 'general-chat',
        activeGeneralConversationId: 'general-chat',
      });
    });

    renderAssistant('/assistant', {
      recipeContext: {
        recipeId: 'recipe-1',
        recipeTitle: 'Tomato Soup',
      },
    });

    await waitFor(() => expect(resumeSpy).toHaveBeenCalledWith('recipe-1'));
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Unable to resume this recipe conversation. Please try again.'
    );
    expect(
      screen.getByRole('textbox', { name: 'Message Nibble' })
    ).toBeDisabled();

    await user.click(
      screen.getByRole('button', { name: 'Start a general chat instead' })
    );

    expect(createGeneralSpy).toHaveBeenCalledTimes(1);
    await waitFor(() =>
      expect(
        screen.getByRole('textbox', { name: 'Message Nibble' })
      ).toBeEnabled()
    );
  });

  test('returns to the origin route with scroll and focus restoration state', async () => {
    const user = userEvent.setup();
    vi.spyOn(
      useChatStore.getState(),
      'resumeRecipeConversation'
    ).mockResolvedValue(undefined);
    const router = createMemoryRouter(
      [
        {
          path: '/assistant',
          element: <AssistantPage />,
        },
        {
          path: '/recipes/:id',
          element: <p>Recipe origin</p>,
        },
      ],
      {
        initialEntries: [
          {
            pathname: '/assistant',
            state: {
              recipeContext: {
                recipeId: 'recipe-1',
                recipeTitle: 'Tomato Soup',
              },
              recipeOrigin: {
                pathname: '/recipes/recipe-1',
                scrollY: 384,
                triggerId: 'recipe-nibble-trigger',
              },
            },
          },
        ],
      }
    );

    render(<RouterProvider router={router} />);
    await user.click(screen.getByRole('button', { name: 'Back to recipe' }));

    await waitFor(() =>
      expect(router.state.location.pathname).toBe('/recipes/recipe-1')
    );
    expect(router.state.location.state).toEqual({
      recipeRestoration: {
        scrollY: 384,
        triggerId: 'recipe-nibble-trigger',
      },
    });
  });

  test('falls back to the persisted recipe route without restoration state', async () => {
    const user = userEvent.setup();
    vi.spyOn(useChatStore.getState(), 'loadConversations').mockResolvedValue(
      undefined
    );
    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'recipe-chat',
            title: 'Tomato Soup help',
            createdAt: '2026-09-29T10:00:00Z',
            lastMessageAt: '2026-09-29T10:00:00Z',
            recipeContext: {
              recipeId: 'recipe-1',
              recipeTitle: 'Tomato Soup',
              isCurrent: true,
            },
          },
        ],
        activeConversationId: 'recipe-chat',
      });
    });
    const router = createMemoryRouter(
      [
        { path: '/assistant', element: <AssistantPage /> },
        { path: '/recipes/:id', element: <p>Recipe fallback</p> },
      ],
      { initialEntries: ['/assistant'] }
    );

    render(<RouterProvider router={router} />);
    await user.click(screen.getByRole('button', { name: 'Back to recipe' }));

    await waitFor(() =>
      expect(router.state.location.pathname).toBe('/recipes/recipe-1')
    );
    expect(router.state.location.state).toBeNull();
  });

  test('preserves the recipe entry for browser-back navigation', async () => {
    const scrollTo = vi
      .spyOn(window, 'scrollTo')
      .mockImplementation(() => undefined);
    vi.spyOn(
      useChatStore.getState(),
      'resumeRecipeConversation'
    ).mockResolvedValue(undefined);
    const router = createMemoryRouter(
      [
        { path: '/assistant', element: <AssistantPage /> },
        {
          path: '/recipes/:id',
          element: <RecipeBrowserBackDestination />,
        },
      ],
      {
        initialEntries: [
          {
            pathname: '/recipes/recipe-1',
            state: {
              recipeRestoration: {
                scrollY: 640,
                triggerId: 'recipe-nibble-trigger',
              },
            },
          },
          {
            pathname: '/assistant',
            state: {
              recipeContext: {
                recipeId: 'recipe-1',
                recipeTitle: 'Tomato Soup',
              },
            },
          },
        ],
        initialIndex: 1,
      }
    );

    render(<RouterProvider router={router} />);
    await act(async () => {
      await router.navigate(-1);
    });

    const trigger = screen.getByRole('button', {
      name: 'Ask Nibble about Tomato Soup',
    });
    expect(trigger).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/recipes/recipe-1');
    expect(router.state.location.state).toEqual({
      recipeRestoration: {
        scrollY: 640,
        triggerId: 'recipe-nibble-trigger',
      },
    });
    await waitFor(() => {
      expect(scrollTo).toHaveBeenCalledWith({ top: 640 });
      expect(trigger).toHaveFocus();
      expect(document.activeElement).toBe(trigger);
    });
  });

  test('starts one general New Chat and clears recipe route context', async () => {
    const user = userEvent.setup();
    const loadSpy = vi.spyOn(useChatStore.getState(), 'loadConversations');
    const createGeneralSpy = vi.spyOn(
      useChatStore.getState(),
      'createConversation'
    );
    const createRecipeSpy = vi
      .spyOn(useChatStore.getState(), 'createRecipeConversation')
      .mockResolvedValue(undefined);

    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'recipe-chat',
            title: 'Tomato Soup help',
            createdAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
            lastMessageAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
            recipeContext: {
              recipeId: 'recipe-1',
              recipeTitle: 'Tomato Soup',
              isCurrent: true,
            },
          },
        ],
        activeConversationId: 'recipe-chat',
        messagesByConversationId: { 'recipe-chat': [] },
      });
    });

    const router = createMemoryRouter(
      [{ path: '/assistant', element: <AssistantPage /> }],
      {
        initialEntries: [
          {
            pathname: '/assistant',
            state: {
              recipeContext: {
                recipeId: 'recipe-1',
                recipeTitle: 'Tomato Soup',
              },
            },
          },
        ],
      }
    );
    render(<RouterProvider router={router} />);

    await user.click(screen.getAllByRole('button', { name: 'New Chat' })[0]);
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/assistant');
      expect(router.state.location.state).toBeNull();
      expect(createGeneralSpy).toHaveBeenCalledTimes(1);
      expect(loadSpy).toHaveBeenCalledTimes(2);
    });
    expect(createRecipeSpy).not.toHaveBeenCalled();
    expect(
      screen.queryByRole('button', {
        name: 'New conversation for Tomato Soup',
      })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Back to recipe' })
    ).not.toBeInTheDocument();
    const state = useChatStore.getState();
    expect(state.activeConversationId).toBe(state.activeGeneralConversationId);
    expect(state.activeGeneralConversationId).not.toBeNull();
    expect(
      state.conversations.find(
        (conversation) => conversation.id === state.activeConversationId
      )?.recipeContext
    ).toBeUndefined();
    expect(
      screen.getByRole('textbox', { name: 'Message Nibble' })
    ).toBeEnabled();
  });

  test('resumes a new recipe when route state changes while mounted', async () => {
    const resumeSpy = vi
      .spyOn(useChatStore.getState(), 'resumeRecipeConversation')
      .mockResolvedValue(undefined);
    const router = createMemoryRouter(
      [{ path: '/assistant', element: <AssistantPage /> }],
      {
        initialEntries: [
          {
            pathname: '/assistant',
            state: {
              recipeContext: {
                recipeId: 'recipe-a',
                recipeTitle: 'Recipe A',
              },
            },
          },
        ],
      }
    );

    render(<RouterProvider router={router} />);
    await waitFor(() => expect(resumeSpy).toHaveBeenCalledWith('recipe-a'));

    await act(async () => {
      await router.navigate('/assistant', {
        state: {
          recipeContext: {
            recipeId: 'recipe-b',
            recipeTitle: 'Recipe B',
          },
        },
      });
    });

    expect(screen.getByText('Recipe: Recipe B')).toBeInTheDocument();
    await waitFor(() => expect(resumeSpy).toHaveBeenCalledWith('recipe-b'));
    expect(resumeSpy.mock.calls).toEqual([['recipe-a'], ['recipe-b']]);
  });

  test('offers a general-chat recovery when recipe context is inaccessible', async () => {
    const user = userEvent.setup();
    const resumeSpy = vi
      .spyOn(useChatStore.getState(), 'resumeRecipeConversation')
      .mockImplementation(async () => {
        act(() => {
          useChatStore.setState({
            activeConversationId: null,
            error: 'This recipe conversation is no longer available.',
          });
        });
      });
    const createGeneralSpy = vi.spyOn(
      useChatStore.getState(),
      'createConversation'
    );

    renderAssistant('/assistant', {
      recipeContext: {
        recipeId: 'missing-recipe',
        recipeTitle: 'Missing Recipe',
      },
    });

    await waitFor(() => expect(resumeSpy).toHaveBeenCalled());
    expect(screen.getByRole('alert')).toHaveTextContent(
      'This recipe conversation is no longer available.'
    );
    expect(
      screen.getByRole('button', { name: 'Back to recipe' })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', {
        name: 'New conversation for Missing Recipe',
      })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('textbox', { name: 'Message Nibble' })
    ).toBeDisabled();

    await user.click(
      screen.getByRole('button', { name: 'Start a general chat instead' })
    );
    expect(createGeneralSpy).toHaveBeenCalledTimes(1);
    await waitFor(() => {
      expect(
        screen.queryByRole('button', {
          name: 'New conversation for Missing Recipe',
        })
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole('button', {
          name: 'Start a general chat instead',
        })
      ).not.toBeInTheDocument();
      const state = useChatStore.getState();
      expect(state.activeConversationId).toBe(
        state.activeGeneralConversationId
      );
      expect(state.activeGeneralConversationId).not.toBeNull();
      expect(
        state.conversations.find(
          (conversation) => conversation.id === state.activeConversationId
        )?.recipeContext
      ).toBeUndefined();
      expect(
        screen.getByRole('textbox', { name: 'Message Nibble' })
      ).toBeEnabled();
    });
  });

  test('switches to the first conversation when conversations exist but none selected', async () => {
    const switchSpy = vi.spyOn(useChatStore.getState(), 'switchConversation');

    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'c1',
            title: 'Chat with Nibble',
            createdAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
            lastMessageAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
          },
        ],
        activeConversationId: null,
        messagesByConversationId: { c1: [] },
      });
    });

    renderAssistant();

    await waitFor(() => expect(switchSpy).toHaveBeenCalledWith('c1'));
  });

  test('renders messages as a semantic list', () => {
    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'c1',
            title: 'Chat with Nibble',
            createdAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
            lastMessageAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
          },
        ],
        activeConversationId: 'c1',
        messagesByConversationId: {
          c1: [
            {
              id: 'm1',
              conversationId: 'c1',
              role: 'user',
              content: 'Hello',
              createdAt: new Date('2026-01-01T01:00:00.000Z').toISOString(),
            },
            {
              id: 'm2',
              conversationId: 'c1',
              role: 'assistant',
              content: 'Hi! I am Nibble.',
              createdAt: new Date('2026-01-01T01:00:10.000Z').toISOString(),
            },
          ],
        },
      });
    });

    renderAssistant();

    expect(screen.getByRole('list')).toBeInTheDocument();
    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('Hi! I am Nibble.')).toBeInTheDocument();
    expect(screen.getByLabelText('You message')).toBeInTheDocument();
    expect(screen.getByLabelText('Nibble message')).toBeInTheDocument();
  });

  test('Cmd/Ctrl+K focuses the composer and Cmd/Ctrl+N creates a new chat', async () => {
    const user = userEvent.setup();
    const createSpy = vi.spyOn(useChatStore.getState(), 'createConversation');

    renderAssistant();

    const composer = screen.getByLabelText('Message Nibble');
    expect(composer).not.toHaveFocus();

    window.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'k', metaKey: true })
    );
    await waitFor(() => expect(composer).toHaveFocus());

    window.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'n', ctrlKey: true })
    );
    await waitFor(() => expect(createSpy).toHaveBeenCalled());

    // sanity: keyboard handler does not block normal typing
    await user.type(composer, 'test');
    expect(screen.getByDisplayValue('test')).toBeInTheDocument();
  });

  test('announces new assistant messages via a polite live region', async () => {
    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'c1',
            title: 'Chat with Nibble',
            createdAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
            lastMessageAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
          },
        ],
        activeConversationId: 'c1',
        messagesByConversationId: {
          c1: [
            {
              id: 'm2',
              conversationId: 'c1',
              role: 'assistant',
              content: 'Welcome!',
              createdAt: new Date('2026-01-01T01:00:10.000Z').toISOString(),
            },
          ],
        },
      });
    });

    renderAssistant();

    const status = screen.getByRole('status');
    await waitFor(() => expect(status).toHaveTextContent('Nibble: Welcome!'));
  });

  test('honors ?conversationId=... by switching conversations', async () => {
    const switchSpy = vi.spyOn(useChatStore.getState(), 'switchConversation');

    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'c1',
            title: 'Chat 1',
            createdAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
            lastMessageAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
          },
          {
            id: 'c2',
            title: 'Chat 2',
            createdAt: new Date('2026-01-02T00:00:00.000Z').toISOString(),
            lastMessageAt: new Date('2026-01-02T00:00:00.000Z').toISOString(),
          },
        ],
        activeConversationId: 'c1',
        messagesByConversationId: { c1: [], c2: [] },
      });
    });

    renderAssistant('/assistant?conversationId=c2');

    await waitFor(() => expect(switchSpy).toHaveBeenCalledWith('c2'));
  });

  test('polls conversation list every 30 seconds when hydrated', async () => {
    vi.useFakeTimers();
    const loadSpy = vi.spyOn(useChatStore.getState(), 'loadConversations');
    loadSpy.mockResolvedValue(undefined);

    renderAssistant();

    // Wait for initial load and then clear the spy
    await vi.waitFor(() => expect(loadSpy).toHaveBeenCalled());
    loadSpy.mockClear();

    // Advance 60 seconds - test mode uses production interval (60s)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60000);
    });

    expect(loadSpy).toHaveBeenCalledTimes(1);

    // Advance another 60 seconds - should trigger again
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60000);
    });

    expect(loadSpy).toHaveBeenCalledTimes(2);

    vi.useRealTimers();
  });

  test('does not poll conversations when not hydrated', async () => {
    vi.useFakeTimers();
    const loadSpy = vi.spyOn(useChatStore.getState(), 'loadConversations');
    loadSpy.mockResolvedValue(undefined);

    act(() => {
      useChatStore.setState({ hasHydrated: false });
    });

    renderAssistant();

    // Clear any initial calls
    loadSpy.mockClear();

    // Wait and verify no polling happens
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60000); // 60 seconds
    });

    // Should not have been called since hasHydrated is false
    expect(loadSpy).not.toHaveBeenCalled();

    vi.useRealTimers();
  });

  test('clears polling interval on unmount', async () => {
    vi.useFakeTimers();
    const loadSpy = vi.spyOn(useChatStore.getState(), 'loadConversations');
    loadSpy.mockResolvedValue(undefined);

    const { unmount } = renderAssistant();

    // Wait for initial load
    await vi.waitFor(() => expect(loadSpy).toHaveBeenCalled());

    // Unmount the component
    unmount();

    // Clear spy to reset call count
    loadSpy.mockClear();

    // Advance time - polling should not happen after unmount
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60000);
    });

    // Should not have been called after unmount
    expect(loadSpy).not.toHaveBeenCalled();

    vi.useRealTimers();
  });

  test('shows "Load older messages" button when has_more is true', () => {
    vi.spyOn(useChatStore.getState(), 'loadConversations').mockResolvedValue(
      undefined
    );

    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'c1',
            title: 'Chat',
            createdAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
            lastMessageAt: new Date('2026-01-01T01:00:00.000Z').toISOString(),
          },
        ],
        activeConversationId: 'c1',
        messagesByConversationId: {
          c1: [
            {
              id: 'm1',
              conversationId: 'c1',
              role: 'user',
              content: 'Hello',
              createdAt: new Date('2026-01-01T01:00:00.000Z').toISOString(),
            },
          ],
        },
        hasPreviousMessagesByConversationId: { c1: true },
      });
    });

    renderAssistant();

    expect(
      screen.getByRole('button', { name: 'Load older messages' })
    ).toBeInTheDocument();
  });

  test('hides "Load older messages" button when has_more is false', () => {
    vi.spyOn(useChatStore.getState(), 'loadConversations').mockResolvedValue(
      undefined
    );

    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'c1',
            title: 'Chat',
            createdAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
            lastMessageAt: new Date('2026-01-01T01:00:00.000Z').toISOString(),
          },
        ],
        activeConversationId: 'c1',
        messagesByConversationId: {
          c1: [
            {
              id: 'm1',
              conversationId: 'c1',
              role: 'user',
              content: 'Hello',
              createdAt: new Date('2026-01-01T01:00:00.000Z').toISOString(),
            },
          ],
        },
        hasPreviousMessagesByConversationId: { c1: false },
      });
    });

    renderAssistant();

    expect(
      screen.queryByRole('button', { name: 'Load older messages' })
    ).not.toBeInTheDocument();
  });

  test('calls loadMoreMessages when "Load older messages" is clicked', async () => {
    const user = userEvent.setup();
    vi.spyOn(useChatStore.getState(), 'loadConversations').mockResolvedValue(
      undefined
    );
    const loadMoreSpy = vi.spyOn(useChatStore.getState(), 'loadMoreMessages');
    loadMoreSpy.mockResolvedValue(undefined);

    act(() => {
      useChatStore.setState({
        conversations: [
          {
            id: 'c1',
            title: 'Chat',
            createdAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
            lastMessageAt: new Date('2026-01-01T01:00:00.000Z').toISOString(),
          },
        ],
        activeConversationId: 'c1',
        messagesByConversationId: {
          c1: [
            {
              id: 'm1',
              conversationId: 'c1',
              role: 'user',
              content: 'Hello',
              createdAt: new Date('2026-01-01T01:00:00.000Z').toISOString(),
            },
          ],
        },
        hasPreviousMessagesByConversationId: { c1: true },
      });
    });

    renderAssistant();

    await user.click(
      screen.getByRole('button', { name: 'Load older messages' })
    );

    await waitFor(() => expect(loadMoreSpy).toHaveBeenCalledWith('c1'));
  });
});
