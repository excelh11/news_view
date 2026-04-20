import React from 'react';
import { useParams } from 'react-router-dom';
import Categories from '../components/Categories';
import NewsList from '../components/NewsList';
import ChatbotNewsSearch from '../components/ChatbotNewsSearch';

const NewsPage = () => {
  const params = useParams(); //http://localhost:5173/business
  const category = params.category || 'all';

  return (
    <>
      <Categories />
      <ChatbotNewsSearch />
      <NewsList category={category} />
    </>
  );
};

export default NewsPage;
