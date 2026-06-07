import "./globals.css";

// Wraps every page. Sets the browser tab title and basic page structure.
export const metadata = {
  title: "Lead Dashboard",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
