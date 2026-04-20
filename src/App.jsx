import { Route, Routes } from 'react-router-dom';
import NewsPage from './pages/NewsPage';

const App = () => {
  return (
    <Routes>
      <Route path="/" element={<NewsPage />} />
      {/* http://localhost:5173/business */}
      <Route path="/:category" element={<NewsPage />} />
    </Routes>
  );
};

export default App;
