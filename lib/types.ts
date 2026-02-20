// Supabase Database Type Definitions

export type Database = {
  public: {
    Tables: {
      users: {
        Row: {
          id: string;
          user_name: string;
          icon: string;
        };
        Insert: {
          user_name: string;
          icon?: string;
        };
        Update: {
          user_name?: string;
          icon?: string;
        };
      };
      categories: {
        Row: {
          id: number;
          name: string;
        };
        Insert: {
          name: string;
        };
        Update: {
          name?: string;
        };
      };
      books: {
        Row: {
          id: string;
          title: string;
          author: string | null;
          category: string | null;
          url: string | null;
          created_by: string | null;
          created_at?: string;
          deleted_at?: string | null;
        };
        Insert: {
          title: string;
          author?: string;
          category?: string;
          url?: string;
          created_by?: string;
        };
        Update: {
          title?: string;
          author?: string;
          category?: string;
          url?: string;
          created_by?: string;
          deleted_at?: string | null;
        };
      };
      votes: {
        Row: {
          id: string;
          created_at: string;
          action: "選出" | "投票";
          book_id: string;
          user_name: string;
          points: number | null;
          comment: string | null;
        };
        Insert: {
          action: "選出" | "投票";
          book_id: string;
          user_name: string;
          points?: number;
          comment?: string;
        };
        Update: {
          action?: "選出" | "投票";
          book_id?: string;
          user_name?: string;
          points?: number;
          comment?: string;
        };
      };
      events: {
        Row: {
          id?: string;
          event_date: string;
          book_id: string;
        };
        Insert: {
          event_date: string;
          book_id: string;
        };
        Update: {
          event_date?: string;
          book_id?: string;
        };
      };
      access_logs: {
        Row: {
          id?: string;
          user_name: string;
          created_at?: string;
        };
        Insert: {
          user_name: string;
        };
        Update: {
          user_name?: string;
        };
      };
    };
  };
};

// App-level types
export type User = Database["public"]["Tables"]["users"]["Row"];
export type Book = Database["public"]["Tables"]["books"]["Row"];
export type Vote = Database["public"]["Tables"]["votes"]["Row"];
export type Event = Database["public"]["Tables"]["events"]["Row"];
export type Category = Database["public"]["Tables"]["categories"]["Row"];

export type EventWithBook = Event & {
  books: Book | null;
};

export type VoteWithBook = Vote & {
  books?: {
    title: string;
    author: string | null;
  };
};

export type NominatedBook = {
  book_id: string;
  user_name: string;
  title: string;
  author: string | null;
  url: string | null;
  total_points: number;
  voters: { user_name: string; icon: string; points: number }[];
};
