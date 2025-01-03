/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
import { genkit as initAgenkit, z } from 'genkit';
import { GoogleAuth } from 'google-auth-library';
import { google } from 'googleapis';
import { initAgents } from './agents.js';

var service = google.youtube('v3');
const client = new GoogleAuth();

const genkit = initAgenkit({
  plugins: [googleAI()],
  model: gemini15Flash,
});

const research = genkit.defineFlow('research', async () => {
  const resp = await service.search.list({
    auth: client.fromAPIKey(process.env.YOUTUBE_API_KEY!) as any,
    part: ['snippet'],
    q: 'genai agent',
    maxResults: 10,
  });
  return resp.data;
});

const fetchRecentVideos = genkit.defineTool(
  {
    name: 'fetchRecentVideos',
    description: 'use to find recent videos on the subject',
    inputSchema: z.object({
      subject: z.string(),
    }),
    outputSchema: z.string(),
  },
  async (input) => {
    return `Title: What are AI Agents?
Description: Want to see Maya Murad explain more about AI Agents? Click here to register for a Virtual Agents Webinar → https://ibm.biz/BdaAVa
Want to play with the technology yourself? Explore our interactive demo → https://ibm.biz/BdKsEf

In this video, Maya Murad explores the evolution of AI agents and their pivotal role in revolutionizing AI systems. From monolithic models to compound AI systems, discover how AI agents integrate with databases and external tools to enhance problem-solving capabilities and adaptability.

AI news moves fast. Sign up for a monthly newsletter for AI updates from IBM → https://www.ibm.com/account/reg/us-en/signup?formid=news-urx-52120


- - NEXT VIDEO - -

Title: What is AI Agent in Artificial Intelligence? | Simple Explanation of an AI Agent
Description: What exactly is an AI Agent? I will explain this topic using a simple analogy in this video. Agentic frameworks such as Langgraph, Crew AI, Microsoft Autogen has become a talk of the town, all of them are based on one central concept "AI Agent".

Dialogflow food order chatbot: https://youtu.be/2e5pQqBvGco?si=VNw1LxRsuIBy95Xr

Do you want to learn technology from me? Check https://codebasics.io/?utm_source=description&utm_medium=yt&utm_campaign=description&utm_id=description for my affordable video courses.

Need help building software or data analytics/AI solutions? My company https://www.atliq.com/ can help. Click on the Contact button on that website.

🎥 Codebasics Hindi channel: https://www.youtube.com/channel/UCTmFBhuhMibVoSfYom1uXEg

#️⃣ Social Media #️⃣

🧑‍🤝‍🧑 Discord for Community Support:  https://discord.gg/r42Kbuk
📸 Codebasics' Instagram: https://www.instagram.com/codebasicshub/
📝 Codebasics' Linkedin :  https://www.linkedin.com/company/codebasics/

------

📝 Dhaval's Linkedin : https://www.linkedin.com/in/dhavalsays/
📝 Hem's Linkedin: https://www.linkedin.com/in/hemvad/

📽️ Hem's Instagram for daily tips: https://www.instagram.com/hemvadivel/
📸 Dhaval's Personal Instagram: https://www.instagram.com/dhavalsays/

🔗 Patreon: https://www.patreon.com/codebasics?fan_landing=true


- - NEXT VIDEO - -

Title: AI Agents Explained: A Comprehensive Guide for Beginners
Description: AI Agents Explained: A Comprehensive Guide for Beginners by Alfie Marsh Co-Founder & CEO of https://www.toolflow.ai/

(0:00) Introduction to AI Agents
(0:23) What is an AI Agent?
(0:49) How AI Agents Differ from Traditional Software
(1:36) AI Agents vs Large Language Models (LLMs)
(2:50) How AI Agents Work
(3:16) Component 1: Planning
(3:47) Component 2: Interacting with Tools
(4:10) Component 3: Memory and External Knowledge
(5:07) Component 4: Executing Actions
(5:39) Risks and Future of AI Agents
(6:30) Conclusion

In this video, Alfie Marsh, Co-Founder & CEO of Toolflow.ai,  unpacks the world of AI agents and explains how they are evolving to become an integral part of our lives. Discover what AI agents are, how they differ from traditional automations and other large language models (LLMs) like GPT, Claude, and Gemini, and explore real-world examples of AI agents in action. 

Learn about the key components that make up AI agents, including their ability to plan, interact with tools, store memory, access external knowledge, and execute actions autonomously. Alfie also discusses the potential risks and the future of AI agents as they become more sophisticated with advancements in language models like GPT-4 and beyond.

Whether you're interested in building AI agents, understanding how they work, or exploring no-code solutions and tutorials, this video provides a comprehensive overview of AI agents and their growing importance in our lives and careers.


- - NEXT VIDEO - -

Title: What is Agentic AI? Important For GEN AI In 2025
Description: Agentic AI, or AI agents, are software systems that can perform tasks autonomously with minimal human intervention. They are designed to be goal-oriented and can interact with data and tools to accomplish tasks. Agentic AI is considered the third wave of artificial intelligence, and it represents a fundamental shift in how people think about and interact with AI. 
--------------------------------------------------------------------------------------------------------
Learn from me and my team
https://www.krishnaik.in/liveclasses
--------------------------------------------------------------------------------------------------------
Join my community channel
Whatsapp channel: whatsapp.com/channel/0029Va9q4Yh2Jl8NIS1oPX01
Instagram: https://instagram.com/krishnaik06
Twitter: twitter.com/Krishnaik06
Disscord: discord.gg/Ca3P7AZ5re


- - NEXT VIDEO - -

Title: Intro to AI agents
Description: Vertex AI Agent Builder quickstart → https://goo.gle/3UPJ7dN
GenAI powered App with Genkit → https://goo.gle/4fCSTrK

Demystifying AI agents, Googlers Aja Hammerly and Jason Davenport provide a comprehensive overview of their capabilities, applications, and construction. Join us as we unravel the diverse definitions, explore compelling use cases, and delve into the different architectural approaches for building intelligent agents.

Chapters:
0:00 - Intro
0:18 - What is an AI agent?
1:54 - Agentic systems examples
3:10 - Agentic architectures
4:57 - Get started building agents 

More resources:
 Oscar, Open source contributor agent  →https://goo.gle/3Z2HqMm
Compass Travel Planning Sample App  → https://goo.gle/4hOczun

Watch more Real Terms for AI → https://goo.gle/AIwordsExplained
Subscribe to Google Cloud Tech → https://goo.gle/GoogleCloudTech

#GoogleCloud #GenerativeAI

Speakers: Aja Hammerly, Jason Davenport
Products Mentioned: Cloud - AI and Machine Learning - Agents, Vertex AI, Gemini


- - NEXT VIDEO - -

Title: What is a Generative AI Agent?
Description: Generative AI Agents represent the current frontier of LLM technology, enabling dynamic interactions and intelligent workflow automation. However, the complexities of architecting and deploying these agents can be daunting. In this live session, Patrick Marlow demystifies the process, guiding you through the critical decisions and trade-offs involved in building production-ready agents.

Explore the full spectrum of Agent development, from the core components like Models, Tools, and Orchestration Frameworks to the strategic choices between managed and DIY approaches. The session wraps up with a live demo and Q&A.

Learn more about Vertex Agents on Google Cloud: https://cloud.google.com/dialogflow/vertex/docs/concept/agents


- - NEXT VIDEO - -

Title: Andrew Ng Explores The Rise Of AI Agents And Agentic Reasoning | BUILD 2024 Keynote
Description: In recent years, the spotlight in AI has primarily been on large language models (LLMs) and emerging large multi-modal models (LMMs). Now, building on these tools, a new paradigm is emerging with the rise of AI agents and agentic reasoning, which are proving to be both cost-effective and powerful for building numerous new applications. As AI continues to evolve, data across all industries—particularly unstructured data such as text, images, video, and audio—is becoming more critical than ever. In this keynote session from BUILD 2024, Andrews Ng, Founder and Executive Chairman of Landing AI, explores the rise of AI, agents, and the growing role of unstructured data. He also discusses how this convergence will shape automation and application building across industries. Check out Andrew Ng on AI agentic workflows and their potential for driving AI progress here:  https://www.youtube.com/watch?v=q1XFm21I-VQ

Register to watch more BUILD on-demand here: https://www.snowflake.com/build/.

❄Join our YouTube community❄ https://bit.ly/3lzfeeB 

Learn more about Snowflake:
➡️ Website: https://www.snowflake.com 
➡️ Careers: http://careers.snowflake.com
➡️ Podcast page: https://www.snowflake.com/thedatacloudpodcast/
➡️ Twitter: https://twitter.com/SnowflakeDB 
➡️ Instagram: https://www.instagram.com/_snowflake_inc
➡️ Facebook: https://www.facebook.com/snowflakedb
➡️ LinkedIn: https://bit.ly/2QUexl4
➡️ Sign up for our weekly live demo program and have your questions answered by a Snowflake expert at https://bit.ly/2TdVCmJ

Listen on: 
🔈 Apple Podcasts: https://apple.co/3cCdrCU 
🔈 Spotify: https://spoti.fi/39vCNjH
🔈 Simplecast: https://bit.ly/3rFCrgA

#Snowflake #DataCloud


- - NEXT VIDEO - -

Title: Generative AI is just the Beginning AI Agents are what Comes next | Daoud Abdel Hadi | TEDxPSUT
Description: Navigate the frontier of artificial intelligence, exploring the transformative potential of generative AI and the emerging era of AI agents. I am a Machine Learning Engineer at EastNets, where I'm responsible for introducing and implementing machine learning to tackle the not-so-easy task of combatting financial crimes such as money laundering, terrorist financing, and fraud. 

I graduated with both a Bachelors and Masters degree in Artificial Intelligence where I fully immersed myself in all things machine learning, from decision trees to state-of-the-art Deep Neural networks. 

I like being able to explain things and dislike being unable to explain something. This is where my field and I fit together perfectly, I get to think of creative and innovative ways to make sense of data for a living and make something useful out of it. This talk was given at a TEDx event using the TED conference format but independently organized by a local community. Learn more at https://www.ted.com/tedx


- - NEXT VIDEO - -

Title: GenAI - SQL Agent
Description: https://app.box.com/s/o9fsx0gwek1r1tvtfbb25z6w4y8tob70


- - NEXT VIDEO - -

Title: Microsoft Launches 10 NEW AI Agents
Description: In this video I look at the new AI Agents Microsoft announced at their Ignite conference and how they are taking on startups in the AI Agents field.

MSFT Agents Chat with Matt Marshall: https://venturebeat.com/ai/microsofts-ai-agents-4-insights-that-could-reshape-the-enterprise-landscape/

Dynamics 365 announcement: https://www.microsoft.com/en-us/dynamics-365/blog/business-leader/2024/10/21/transform-work-with-autonomous-agents-across-your-business-processes/

For more tutorials on using LLMs and building agents, check out my Patreon
Patreon: https://www.patreon.com/SamWitteveen
Twitter: https://twitter.com/Sam_Witteveen

🕵️ Interested in building LLM Agents? Fill out the form below
Building LLM Agents Form: https://drp.li/dIMes

👨‍💻Github:
https://github.com/samwit/langchain-tutorials (updated)
https://github.com/samwit/llm-tutorials

⏱️Time Stamps:
00:00 Intro
00:27 Microsoft Blog
03:16 Sales Qualification Agent
04:07 Sales Order Agent
04:50 Supplier Communications Agent
06:00 Financial Reconciliation Agent
06:47 Time and Expense Agent
07:23 Customer Intent Agent
09:40 Scheduling Operations Agent
12:05 VentureBeat`;

    const resp = await service.search.list({
      auth: client.fromAPIKey(process.env.YOUTUBE_API_KEY!) as any,
      part: ['snippet'],
      q: input.subject,
      maxResults: 10,
    });

    const videos = await service.videos.list({
      auth: client.fromAPIKey(process.env.YOUTUBE_API_KEY!) as any,
      id: (resp.data.items as any[]).map((v) => v.id.videoId),
      part: ['snippet'],
    });
    return (
      videos?.data?.items
        ?.map(
          (v) =>
            `Title: ${v.snippet?.title}\nDescription: ${v.snippet?.description}`
        )
        .join('\n\n\n- - NEXT VIDEO - -\n\n') ?? ''
    );
  }
);

const ai = initAgents(genkit);

const scriptWriterAgent = ai.defineAgent({
  name: 'scriptWriterAgent',
  description: 'can write a video script',
  instructions:
    `You are a video script writer. Use the video title and description ` +
    `that was previously generated and use it to write a detaield script for the video. State it and `,
  tools: ['creatorAgent'],
  toolChoice: 'required',
});

const outputAgent = ai.defineAgent({
  name: 'outputAgent',
  description: 'will review the video script and output it to the user',
  instructions: `Look at the last iteration of the video script and output it to the user verbatim.`,
});

const scriptReviewerAgent = ai.defineAgent({
  name: 'scriptReviewerAgent',
  description: 'can review the script for quality',
  instructions: `You are a reviewer. Review the video script. If it looks fine, say it's fine, if it needs more work state your suggestions and transfer to the scriptWriterAgent.`,
  tools: ['creatorAgent'],
  toolChoice: 'required',
});

const creatorAgent = ai.defineAgent({
  name: 'creatorAgent',
  description:
    'helps the user to come up with a video idea on the given subject',
  instructions: `you are helping a youtuber come up with a next video idea. They will give you a subject.
    Your job is to do some research first by fetching recent videos on the subject.
    Come up with a good search term. Once you have some recent videos, call the scriptWriterAgent to write the script.
    Once the script is written, call the scriptReviewerAgent to review the script, if changes required call scriptWriterAgent
    to iterate (ask scriptReviewerAgent to review the final version). Once the reviewer is happy, call outputAgent to 
    produce the final response.`,
  tools: [
    fetchRecentVideos,
    scriptWriterAgent,
    scriptReviewerAgent,
    outputAgent,
  ],
  toolChoice: 'required',
});

async () => {
  const session = ai.startSession({
    agent: creatorAgent,
  });

  const { text } = await session.send('genai agent frameworks');
  console.log(text);
};

(async () => {
  const resp = await genkit.generate({
    prompt:
      'you are a video script writer agent, write the script for a funny video and then call the scriptReviewerAgent',
    model: gemini15Flash,
    tools: [scriptReviewerAgent],
    returnToolRequests: true,
  });
  console.log(' - - ', JSON.stringify(resp.message, undefined, 2));
})();
